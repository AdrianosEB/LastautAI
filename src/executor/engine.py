"""Workflow execution engine — walks steps in order and runs each one."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from src.executor.actions import get_executor

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    step_id: str
    action: str
    status: str  # "success", "failed", "skipped"
    output: Any = None
    error: str | None = None
    duration_seconds: float = 0.0


@dataclass
class ExecutionResult:
    workflow_name: str
    status: str  # "completed", "failed", "partial"
    steps: list[StepResult] = field(default_factory=list)
    total_duration_seconds: float = 0.0


def execute_workflow(workflow: dict) -> ExecutionResult:
    """Execute a workflow definition step by step."""
    start = time.monotonic()
    name = workflow.get("name", "Untitled")
    steps = workflow.get("steps", [])
    error_handling = workflow.get("error_handling", {})
    on_failure = error_handling.get("on_failure", "stop")

    logger.info("Executing workflow: %s (%d steps)", name, len(steps))

    result = ExecutionResult(workflow_name=name, status="completed")

    # Context holds outputs from previous steps, keyed by step_id
    context: dict[str, Any] = {}

    for step in steps:
        step_id = step["id"]
        action = step["action"]
        description = step.get("description", "")
        inputs = step.get("inputs", {})
        conditions = step.get("conditions", {})

        # Check conditions
        if conditions and conditions.get("if"):
            condition_expr = conditions["if"]
            if not _evaluate_condition(condition_expr, context):
                logger.info("Step %s skipped: condition '%s' not met", step_id, condition_expr)
                result.steps.append(StepResult(
                    step_id=step_id, action=action, status="skipped",
                ))
                continue

        # Resolve input references like ${step_1.output}
        resolved_inputs = _resolve_inputs(inputs, context)

        logger.info("Step %s [%s]: %s", step_id, action, description)
        t0 = time.monotonic()

        try:
            executor = get_executor(action)
            output = executor(
                action=action,
                description=description,
                inputs=resolved_inputs,
                context=context,
            )
            duration = time.monotonic() - t0
            logger.info("Step %s completed in %.2fs", step_id, duration)

            step_result = StepResult(
                step_id=step_id, action=action, status="success",
                output=output, duration_seconds=duration,
            )
            context[step_id] = output

        except Exception as e:
            duration = time.monotonic() - t0
            logger.error("Step %s failed: %s", step_id, str(e))

            step_result = StepResult(
                step_id=step_id, action=action, status="failed",
                error=str(e), duration_seconds=duration,
            )

            if on_failure == "stop":
                result.steps.append(step_result)
                result.status = "failed"
                break
            elif on_failure == "skip":
                context[step_id] = None
            elif on_failure == "notify":
                context[step_id] = None

        result.steps.append(step_result)

    result.total_duration_seconds = time.monotonic() - start
    if result.status != "failed":
        result.status = "completed" if all(s.status != "failed" for s in result.steps) else "partial"

    logger.info("Workflow '%s' %s in %.2fs", name, result.status, result.total_duration_seconds)
    return result


def _resolve_inputs(inputs: dict, context: dict) -> dict:
    """Replace ${step_id.field} references with actual values from context."""
    resolved = {}
    for key, value in inputs.items():
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            ref = value[2:-1]  # e.g. "step_1.output"
            parts = ref.split(".", 1)
            step_id = parts[0]
            if step_id in context and context[step_id] is not None:
                if len(parts) > 1 and isinstance(context[step_id], dict):
                    resolved[key] = context[step_id].get(parts[1], value)
                else:
                    resolved[key] = context[step_id]
            else:
                resolved[key] = value
        else:
            resolved[key] = value
    return resolved


def _evaluate_condition(expression: str, context: dict) -> bool:
    """Evaluate a simple condition expression against the execution context.

    Supports basic comparisons like 'step_1.status == success' and
    'step_1.output.count > 0'. Falls back to True for complex expressions
    that can't be parsed statically.
    """
    if not expression or not expression.strip():
        return True

    expr = expression.strip()

    # Handle simple equality: "step_1.status == success"
    for op, fn in [("!=", lambda a, b: a != b), ("==", lambda a, b: a == b),
                   (">=", lambda a, b: float(a) >= float(b)),
                   ("<=", lambda a, b: float(a) <= float(b)),
                   (">", lambda a, b: float(a) > float(b)),
                   ("<", lambda a, b: float(a) < float(b))]:
        if op in expr:
            left, right = [s.strip().strip('"').strip("'") for s in expr.split(op, 1)]
            # Resolve left side from context (e.g. "step_1.status")
            val = _resolve_dotpath(left, context)
            if val is not None:
                try:
                    return fn(str(val), right)
                except (ValueError, TypeError):
                    return True
            break

    return True


def _resolve_dotpath(path: str, context: dict):
    """Resolve a dot-separated path like 'step_1.output.count' from context."""
    parts = path.split(".")
    current = context
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current
