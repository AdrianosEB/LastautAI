import json
from pathlib import Path

from fastapi import APIRouter
import jsonschema

from src.api.models.requests import ValidateRequest

router = APIRouter()

SCHEMA_PATH = Path(__file__).parent.parent.parent.parent / "schemas" / "workflow.schema.json"


def _load_schema() -> dict:
    with open(SCHEMA_PATH) as f:
        return json.load(f)


@router.post("/workflows/validate")
async def validate(request: ValidateRequest):
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
