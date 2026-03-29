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
    return [_workflow_summary(w) for w in workflows]


def _workflow_summary(w: Workflow) -> dict:
    """Build a workflow summary with trigger type and actionable URLs."""
    try:
        data = w.get_workflow()
        trigger = data.get("trigger", {})
        trigger_type = trigger.get("type", "manual")
        cron = trigger.get("config", {}).get("cron", "")
    except Exception:
        trigger_type, cron = "manual", ""

    summary = {
        "id": w.id,
        "name": w.name,
        "description": w.description,
        "n8n_id": w.n8n_id,
        "trigger_type": trigger_type,
        "created_at": w.created_at.isoformat() if w.created_at else None,
    }
    if trigger_type in ("webhook", "event"):
        summary["webhook_url"] = f"/workflows/{w.id}/trigger"
    if trigger_type == "schedule" and cron:
        summary["schedule_url"] = f"/workflows/{w.id}/schedule"
        summary["cron"] = cron
    return summary


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


@router.post("/workflows/{workflow_id}/schedule")
def schedule_workflow_route(
    workflow_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Schedule a saved workflow to run on a recurring interval.

    Reads the trigger.config.cron field from the workflow definition.
    Also accepts ?cron= query param to override. Supports standard cron
    expressions and simple intervals like 'every 5m'.
    """
    from src.scheduler import schedule_workflow

    w = db.query(Workflow).filter(Workflow.id == workflow_id, Workflow.user_id == user.id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow_data = w.get_workflow()
    cron_expr = workflow_data.get("trigger", {}).get("config", {}).get("cron", "")
    if not cron_expr:
        raise HTTPException(status_code=400, detail="Workflow has no cron schedule in trigger config")

    result = schedule_workflow(w.id, user.id, w.description, workflow_data, cron_expr)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/workflows/{workflow_id}/schedule")
def unschedule_workflow_route(
    workflow_id: int,
    user: User = Depends(get_current_user),
):
    """Stop a scheduled workflow."""
    from src.scheduler import unschedule_workflow
    removed = unschedule_workflow(workflow_id)
    if not removed:
        raise HTTPException(status_code=404, detail="No active schedule for this workflow")
    return {"unscheduled": True}


@router.get("/workflows/schedules")
def list_schedules(user: User = Depends(get_current_user)):
    """List all active workflow schedules for the current user."""
    from src.scheduler import get_schedules
    return {"schedules": get_schedules()}


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
