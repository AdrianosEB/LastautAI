import json

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.api.models.requests import GenerateRequest
from src.auth.dependencies import get_optional_user
from src.db.database import get_db
from src.db.models import User, Workflow
from src.pipeline import generate_workflow_steps

router = APIRouter()


@router.post("/workflows/generate-steps")
async def generate_steps(
    request: GenerateRequest,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    try:
        stages = generate_workflow_steps(
            description=request.description,
            output_format=request.output_format,
            strict_mode=request.strict_mode,
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "pipeline_error", "stage": "unknown", "message": str(e)},
        )

    # Check if analyzer flagged ambiguity
    if stages.get("analyzer", {}).get("status") == "ambiguous":
        return JSONResponse(
            status_code=422,
            content={
                "error": "ambiguous_input",
                "stages": stages,
            },
        )

    # Check if any stage errored
    for stage_name in ("parser", "analyzer", "planner", "serializer"):
        if stages.get(stage_name, {}).get("status") == "error":
            return JSONResponse(
                status_code=500,
                content={
                    "error": "pipeline_error",
                    "stage": stage_name,
                    "message": stages[stage_name].get("error", "Unknown error"),
                    "stages": stages,
                },
            )

    # Save workflow if user is authenticated
    workflow_data = stages.get("workflow")
    if user and workflow_data:
        w = Workflow(
            user_id=user.id,
            name=workflow_data.get("name", "Untitled Workflow"),
            description=request.description,
            workflow_json=json.dumps(workflow_data),
        )
        db.add(w)
        db.commit()
        db.refresh(w)
        stages["saved_id"] = w.id

    return stages
