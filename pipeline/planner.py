from __future__ import annotations

from dataclasses import dataclass, field

from pipeline.graph.dag import DAG
from pipeline.analyzer import AnalysisResult


@dataclass
class TriggerPlan:
    type: str
    cron: str | None = None
    event_type: str | None = None
    webhook_path: str | None = None


@dataclass
class ParameterPlan:
    name: str
    type: str
    default: str | None = None
    description: str = ""


@dataclass
class ErrorHandlingPlan:
    max_attempts: int = 3
    backoff: str = "fixed"
    delay_seconds: int = 5
    on_failure: str = "stop"
    step_overrides: dict[str, dict] = field(default_factory=dict)


@dataclass
class PlanResult:
    dag: DAG
    trigger: TriggerPlan
    parameters: list[ParameterPlan] = field(default_factory=list)
    error_handling: ErrorHandlingPlan = field(default_factory=ErrorHandlingPlan)
    assumptions: list[str] = field(default_factory=list)
    ambiguities: list[dict] = field(default_factory=list)


def _determine_trigger(analysis: AnalysisResult) -> TriggerPlan:
    for cue in analysis.temporal_cues:
        cue_type = cue.get("type", "")
        if cue_type == "schedule" and cue.get("cron"):
            return TriggerPlan(type="schedule", cron=cue["cron"])
        if cue_type == "event":
            return TriggerPlan(type="event", event_type=cue.get("text", "unknown_event"))
    for cond in analysis.conditions:
        if cond.get("type") == "when":
            return TriggerPlan(type="event", event_type=cond.get("expression", ""))
    return TriggerPlan(type="manual")


def _extract_parameters(analysis: AnalysisResult) -> list[ParameterPlan]:
    return [
        ParameterPlan(
            name=raw["name"],
            type=raw.get("type", "string"),
            default=raw.get("value"),
            description=f"Parameter: {raw['name']}",
        )
        for raw in analysis.raw_parameters
    ]


def plan(analysis: AnalysisResult) -> PlanResult:
    dag = DAG()

    for action in analysis.resolved_actions:
        metadata = {
            "action": action.catalog_action.action_id if action.catalog_action else action.verb,
            "description": action.original_text,
            "verb": action.verb,
            "object": action.object,
            "inputs": dict(action.inputs),
            "outputs": dict(action.outputs),
        }
        if action.catalog_action:
            metadata["catalog_action_id"] = action.catalog_action.action_id
        dag.add_node(action.step_id, metadata)

    for i in range(len(analysis.ordering) - 1):
        current = analysis.ordering[i]
        next_step = analysis.ordering[i + 1]
        condition = None
        if i < len(analysis.conditions):
            cond = analysis.conditions[i]
            if cond and cond.get("expression"):
                condition = cond["expression"]
        dag.add_edge(current, next_step, condition=condition)

    trigger = _determine_trigger(analysis)
    parameters = _extract_parameters(analysis)

    return PlanResult(
        dag=dag,
        trigger=trigger,
        parameters=parameters,
        error_handling=ErrorHandlingPlan(),
        assumptions=list(analysis.assumptions),
        ambiguities=[{"text": a.text, "options": a.options} for a in analysis.ambiguities],
    )
