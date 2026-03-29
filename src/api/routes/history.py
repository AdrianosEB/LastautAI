"""Workflow history CRUD and webhook trigger execution."""

import json
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.auth.dependencies import get_current_user
from src.db.database import get_db
from src.db.models import User, Workflow

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/workflows/history")
def list_workflows(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workflows = (
        db.query(Workflow)
        .filter(Workflow.user_id == user.id)
        .order_by(Workflow.created_at.desc())
        .all()
    )
    return [
        {
            "id": w.id,
            "name": w.name,
            "description": w.description,
            "n8n_id": w.n8n_id,
            "has_webhook": _has_webhook_trigger(w),
            "created_at": w.created_at.isoformat() if w.created_at else None,
        }
        for w in workflows
    ]


def _has_webhook_trigger(w: Workflow) -> bool:
    """Check if a workflow's trigger type is webhook or event."""
    try:
        data = w.get_workflow()
        trigger_type = data.get("trigger", {}).get("type", "")
        return trigger_type in ("webhook", "event")
    except Exception:
        return False


@router.get("/workflows/history/{workflow_id}")
def get_workflow(workflow_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    w = db.query(Workflow).filter(Workflow.id == workflow_id, Workflow.user_id == user.id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {
        "id": w.id,
        "name": w.name,
        "description": w.description,
        "workflow": w.get_workflow(),
        "n8n_id": w.n8n_id,
        "created_at": w.created_at.isoformat() if w.created_at else None,
    }


@router.delete("/workflows/history/{workflow_id}")
async def delete_workflow(
    workflow_id: int,
    n8n_url: str = Query(default=""),
    n8n_api_key: str = Query(default=""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    w = db.query(Workflow).filter(Workflow.id == workflow_id, Workflow.user_id == user.id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Workflow not found")

    n8n_deleted = False
    if w.n8n_id and n8n_url and n8n_api_key:
        try:
            url = n8n_url.rstrip("/") + "/api/v1/workflows/" + w.n8n_id
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(
                    url,
                    headers={"X-N8N-API-KEY": n8n_api_key},
                )
            n8n_deleted = resp.status_code in (200, 204)
            if not n8n_deleted:
                logger.warning("n8n delete returned %d for workflow %s", resp.status_code, w.n8n_id)
        except Exception as exc:
            logger.warning("Failed to delete from n8n: %s", exc)

    db.delete(w)
    db.commit()
    return {"deleted": True, "n8n_deleted": n8n_deleted}


@router.post("/workflows/{workflow_id}/trigger")
async def trigger_workflow(
    workflow_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Webhook trigger — execute a saved workflow via HTTP POST.

    Any external system can POST to this URL with a JSON payload.
    The payload is injected as context into the AI execution engine,
    which runs the workflow step by step using Claude's tool use.

    No authentication required — this is a webhook endpoint meant to
    be called by external services (n8n, Zapier, cron jobs, etc.).
    """
    from src.api.routes.execute_ai import run_workflow_stream

    w = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Workflow not found")

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    extra = f"Incoming webhook payload:\n{json.dumps(payload, indent=2)}" if payload else ""

    logger.info("Webhook trigger for workflow %d (%s)", w.id, w.name)
    return StreamingResponse(
        run_workflow_stream(w.description, w.get_workflow(), extra_context=extra),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
