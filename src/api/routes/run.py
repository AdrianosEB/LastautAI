from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.pipeline import generate_workflow, AmbiguityRejection, PipelineError
from src.executor.engine import execute_workflow

router = APIRouter()


class RunRequest(BaseModel):
    description: str = Field(..., min_length=1, description="Natural language task description")
    strict_mode: bool = Field(default=False, description="Reject ambiguous input if true")


@router.post("/workflows/run")
async def run(request: RunRequest):
    """Generate a workflow from a description and execute it immediately."""

    # Step 1: Generate the workflow
    try:
        workflow = generate_workflow(
            description=request.description,
            output_format="json",
            strict_mode=request.strict_mode,
        )
    except AmbiguityRejection as e:
        return JSONResponse(
            status_code=422,
            content={
                "error": "ambiguous_input",
                "message": "Input is ambiguous and strict_mode is enabled",
                "ambiguities": e.ambiguities,
            },
        )
    except PipelineError as e:
        return JSONResponse(
            status_code=500,
            content={"error": "pipeline_error", "stage": e.stage, "message": e.message},
        )

    # Step 2: Execute the workflow
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
