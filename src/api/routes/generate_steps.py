from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.api.models.requests import GenerateRequest
from src.pipeline import generate_workflow_steps

router = APIRouter()


@router.post("/workflows/generate-steps")
async def generate_steps(request: GenerateRequest):
    stages = generate_workflow_steps(
        description=request.description,
        output_format=request.output_format,
        strict_mode=request.strict_mode,
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

    return stages
