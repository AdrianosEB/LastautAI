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
        max_tokens=600,
        messages=[{"role": "user", "content": f"""You are converting a screen-activity analysis into a practical n8n workflow automation prompt.

Here is the AI analysis of a user's screen activity:

"{description}"

IMPORTANT: Focus on the CORE task only. Strip away noise like opening apps, clicking around, or window management. Identify the actual valuable work being done and how to automate it with real integrations (APIs, webhooks, email, Slack, databases, HTTP requests, etc.).

Return TWO sections separated by "---":

SECTION 1 - TITLE: A short title (max 10 words). Action-oriented, describing what the automation DOES.
Example: "Sync CRM contacts to spreadsheet daily"

---

SECTION 2 - WORKFLOW PROMPT: A clear workflow description for an n8n automation. Include:
- TRIGGER: What starts the workflow (webhook, schedule, app event)
- STEPS: The key actions in order, using real services/APIs (not "open app" — instead "fetch data from X API", "send email via Gmail", "post to Slack channel")
- OUTPUT: What the end result is

Keep it practical and implementable. Only include steps that n8n can actually automate via its node integrations. Skip manual UI interactions that can't be automated.

Example:
Sync new CRM deals to team Slack channel
---
When a new deal is created in HubSpot (webhook trigger), fetch the deal details including contact info and value. Format a summary message with the deal name, value, and assigned rep. Post the summary to the #sales-updates Slack channel. If the deal value exceeds $10,000, also send an email notification to the sales manager.

Now generate for the activity above. Return ONLY the title, then "---", then the workflow prompt. Nothing else."""}],
    )
    text = next((b.text for b in resp.content if b.type == "text"), "").strip()
    parts = text.split("---", 1)
    summary = parts[0].strip().strip('"') if parts else description[:100]
    refined = parts[1].strip() if len(parts) > 1 else description
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
