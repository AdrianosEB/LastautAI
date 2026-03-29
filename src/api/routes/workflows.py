"""Consolidated workflow routes: generate, generate-steps, validate, and run."""

import json

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.models.requests import GenerateRequest, ValidateRequest
from src.auth.dependencies import get_optional_user
from src.db.database import get_db
from src.db.models import User, Workflow
from src.pipeline import generate_workflow, generate_workflow_steps, AmbiguityRejection, PipelineError

router = APIRouter()

SCHEMA_PATH = None
_schema_cache = None


def _load_schema() -> dict:
    global SCHEMA_PATH, _schema_cache
    if _schema_cache is None:
        from pathlib import Path
        SCHEMA_PATH = Path(__file__).parent.parent.parent.parent / "schemas" / "workflow.schema.json"
        with open(SCHEMA_PATH) as f:
            _schema_cache = json.load(f)
    return _schema_cache


def _handle_pipeline_error(exc: Exception) -> JSONResponse:
    """Shared error handler for pipeline exceptions."""
    if isinstance(exc, AmbiguityRejection):
        return JSONResponse(
            status_code=422,
            content={
                "error": "ambiguous_input",
                "message": "Input is ambiguous and strict_mode is enabled",
                "ambiguities": exc.ambiguities,
            },
        )
    if isinstance(exc, PipelineError):
        return JSONResponse(
            status_code=500,
            content={"error": "pipeline_error", "stage": exc.stage, "message": exc.message},
        )
    return JSONResponse(
        status_code=500,
        content={"error": "pipeline_error", "stage": "unknown", "message": str(exc)},
    )


@router.post("/workflows/generate")
async def generate(request: GenerateRequest):
    """Generate a workflow definition from a natural language description."""
    try:
        result = generate_workflow(
            description=request.description,
            output_format=request.output_format,
            strict_mode=request.strict_mode,
        )
    except Exception as e:
        return _handle_pipeline_error(e)

    if request.output_format == "yaml":
        return PlainTextResponse(content=result, media_type="text/yaml")
    return result


@router.post("/workflows/generate-steps")
async def generate_steps(
    request: GenerateRequest,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Generate a workflow with intermediate pipeline stage results.

    Returns parser/analyzer/planner/serializer outputs with timing.
    Auto-saves for authenticated users. Auto-detects webhook and
    schedule triggers, returning actionable URLs in the response.
    """
    try:
        stages = generate_workflow_steps(
            description=request.description,
            output_format=request.output_format,
            strict_mode=request.strict_mode,
        )
    except Exception as e:
        return _handle_pipeline_error(e)

    if stages.get("analyzer", {}).get("status") == "ambiguous":
        return JSONResponse(
            status_code=422,
            content={"error": "ambiguous_input", "stages": stages},
        )

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

        # Auto-detect trigger type and surface actionable URLs
        trigger_type = workflow_data.get("trigger", {}).get("type", "manual")
        if trigger_type in ("webhook", "event"):
            stages["webhook_url"] = f"/workflows/{w.id}/trigger"
        if trigger_type == "schedule":
            cron = workflow_data.get("trigger", {}).get("config", {}).get("cron", "")
            if cron:
                stages["schedule_url"] = f"/workflows/{w.id}/schedule"
                stages["cron"] = cron

    return stages


@router.post("/workflows/validate")
async def validate(request: ValidateRequest):
    """Validate a workflow definition against the JSON Schema contract."""
    import jsonschema
    schema = _load_schema()
    try:
        jsonschema.validate(instance=request.workflow, schema=schema)
        return {"valid": True}
    except jsonschema.ValidationError as e:
        return {
            "valid": False,
            "errors": [
                {
                    "path": ".".join(str(p) for p in e.absolute_path) or "$",
                    "message": e.message,
                }
            ],
        }


class RunRequest(BaseModel):
    description: str = Field(..., min_length=1)
    strict_mode: bool = Field(default=False)


@router.post("/workflows/run")
async def run(request: RunRequest):
    """Generate a workflow from a description and execute it immediately."""
    from src.executor.engine import execute_workflow

    try:
        workflow = generate_workflow(
            description=request.description,
            output_format="json",
            strict_mode=request.strict_mode,
        )
    except Exception as e:
        return _handle_pipeline_error(e)

    try:
        result = execute_workflow(workflow)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "execution_error", "message": str(e)},
        )

    return {
        "workflow": workflow,
        "execution": {
            "status": result.status,
            "total_duration_seconds": round(result.total_duration_seconds, 2),
            "steps": [
                {
                    "step_id": s.step_id,
                    "action": s.action,
                    "status": s.status,
                    "output": s.output,
                    "error": s.error,
                    "duration_seconds": round(s.duration_seconds, 2),
                }
                for s in result.steps
            ],
        },
    }
