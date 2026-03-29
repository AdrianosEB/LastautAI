from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse

from src.api.models.requests import GenerateRequest
from src.pipeline import generate_workflow, AmbiguityRejection, PipelineError

router = APIRouter()


@router.post("/workflows/generate")
async def generate(request: GenerateRequest):
    try:
        result = generate_workflow(
            description=request.description,
            output_format=request.output_format,
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

    if request.output_format == "yaml":
        return PlainTextResponse(content=result, media_type="text/yaml")
    return result
