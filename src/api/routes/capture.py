import anthropic
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.auth.dependencies import get_current_user
from src.capture import recorder
from src.db.database import get_db
from src.db.models import User, WorkflowSuggestion

router = APIRouter(prefix="/capture")

_ai = anthropic.Anthropic()


class SuggestionUpdate(BaseModel):
    status: str  # "approved" or "dismissed"


def _refine_suggestion(description: str) -> tuple[str, str]:
    """Use AI to create a short summary and a clean workflow prompt from a raw suggestion."""
    resp = _ai.messages.create(
        model="claude-haiku-4-5",
        max_tokens=400,
        messages=[{"role": "user", "content": f"""Given this AI-detected activity pattern:

"{description}"

Return exactly two lines:
LINE 1: A short summary (max 15 words) describing the workflow in plain language. Example: "Auto-send weekly sales report email every Monday"
LINE 2: A clear, detailed workflow description that could be given to an automation tool to build the workflow. Be specific about triggers, steps, and actions.

Return ONLY the two lines, nothing else."""}],
    )
    text = next((b.text for b in resp.content if b.type == "text"), "")
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    summary = lines[0] if lines else description[:100]
    refined = lines[1] if len(lines) > 1 else description
    return summary, refined


@router.post("/start")
def start_recording(user: User = Depends(get_current_user)):
    started = recorder.start(user.id)
    return {"status": "started" if started else "already_running"}


@router.post("/stop")
def stop_recording(user: User = Depends(get_current_user)):
    stopped = recorder.stop(user.id)
    return {"status": "stopped" if stopped else "not_running"}


@router.get("/status")
def recording_status(user: User = Depends(get_current_user)):
    return {"recording": recorder.is_running(user.id)}


@router.get("/suggestions")
def get_suggestions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    suggestions = (
        db.query(WorkflowSuggestion)
        .filter(WorkflowSuggestion.user_id == user.id)
        .order_by(WorkflowSuggestion.created_at.desc())
        .limit(50)
        .all()
    )
    return {
        "suggestions": [
            {
                "id": s.id,
                "description": s.description,
                "summary": s.summary or "",
                "refined_prompt": s.refined_prompt or "",
                "status": s.status,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in suggestions
        ]
    }


@router.post("/suggestions/{suggestion_id}")
def update_suggestion(
    suggestion_id: int,
    body: SuggestionUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = db.query(WorkflowSuggestion).filter(
        WorkflowSuggestion.id == suggestion_id,
        WorkflowSuggestion.user_id == user.id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    if body.status not in ("approved", "dismissed"):
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'dismissed'")
    s.status = body.status

    # When approving, refine the suggestion with AI
    if body.status == "approved" and not s.refined_prompt:
        try:
            summary, refined = _refine_suggestion(s.description)
            s.summary = summary
            s.refined_prompt = refined
        except Exception as exc:
            print(f"[Capture] Refine error: {exc}")
            s.summary = s.description[:100]
            s.refined_prompt = s.description

    db.commit()
    return {
        "id": s.id,
        "status": s.status,
        "summary": s.summary or "",
        "refined_prompt": s.refined_prompt or "",
    }


@router.delete("/suggestions/{suggestion_id}")
def delete_suggestion(
    suggestion_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = db.query(WorkflowSuggestion).filter(
        WorkflowSuggestion.id == suggestion_id,
        WorkflowSuggestion.user_id == user.id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    db.delete(s)
    db.commit()
    return {"deleted": True}
