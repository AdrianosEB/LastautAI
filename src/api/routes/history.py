from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.auth.dependencies import get_current_user
from src.db.database import get_db
from src.db.models import User, Workflow

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
            "created_at": w.created_at.isoformat() if w.created_at else None,
        }
        for w in workflows
    ]


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
def delete_workflow(workflow_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    w = db.query(Workflow).filter(Workflow.id == workflow_id, Workflow.user_id == user.id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db.delete(w)
    db.commit()
    return {"deleted": True}
