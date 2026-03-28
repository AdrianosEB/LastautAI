from pydantic import BaseModel, Field
from typing import Literal


class GenerateRequest(BaseModel):
    description: str = Field(..., min_length=1, description="Natural language task description")
    output_format: Literal["json", "yaml"] = Field(default="json", description="Output format")
    strict_mode: bool = Field(default=False, description="Reject ambiguous input if true")


class ValidateRequest(BaseModel):
    """Accepts a raw workflow definition body for validation."""
    workflow: dict = Field(..., description="Workflow definition object to validate")
