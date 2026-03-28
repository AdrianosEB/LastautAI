from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Literal


class TriggerConfig(BaseModel):
    cron: str | None = None
    event_type: str | None = None
    webhook_path: str | None = None


class Trigger(BaseModel):
    type: Literal["schedule", "event", "manual", "webhook"]
    config: TriggerConfig = Field(default_factory=TriggerConfig)


class StepCondition(BaseModel):
    if_: str = Field(alias="if", serialization_alias="if")


class Step(BaseModel):
    id: str
    action: str
    description: str
    inputs: dict[str, str] = Field(default_factory=dict)
    outputs: dict[str, str] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)
    conditions: StepCondition | None = None

    model_config = {"populate_by_name": True}


class Parameter(BaseModel):
    name: str
    type: Literal["string", "number", "boolean", "array"]
    default: Any = None
    description: str = ""


class RetryConfig(BaseModel):
    max_attempts: int = 3
    backoff: Literal["fixed", "exponential"] = "fixed"
    delay_seconds: int = 5


class StepOverride(BaseModel):
    max_attempts: int | None = None
    on_failure: Literal["stop", "skip", "notify"] | None = None


class ErrorHandling(BaseModel):
    default_retry: RetryConfig = Field(default_factory=RetryConfig)
    on_failure: Literal["stop", "skip", "notify"] = "stop"
    step_overrides: dict[str, StepOverride] = Field(default_factory=dict)


class WorkflowDefinition(BaseModel):
    name: str
    trigger: Trigger
    steps: list[Step]
    parameters: list[Parameter] = Field(default_factory=list)
    error_handling: ErrorHandling = Field(default_factory=ErrorHandling)
    assumptions: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class Ambiguity(BaseModel):
    text: str
    options: list[str]


class AmbiguityError(BaseModel):
    error: Literal["ambiguous_input"] = "ambiguous_input"
    message: str
    ambiguities: list[Ambiguity]


class ValidationError_(BaseModel):
    path: str
    message: str


class ValidationResult(BaseModel):
    valid: bool
    errors: list[ValidationError_] = Field(default_factory=list)
