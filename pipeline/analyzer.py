from __future__ import annotations

from dataclasses import dataclass, field

from pipeline.catalog.registry import ActionRegistry, Action, create_registry
from pipeline.parser import ParseResult


@dataclass
class ResolvedAction:
    step_id: str
    catalog_action: Action | None
    verb: str
    object: str
    original_text: str
    inputs: dict[str, str] = field(default_factory=dict)
    outputs: dict[str, str] = field(default_factory=dict)


@dataclass
class AmbiguityFlag:
    text: str
    options: list[str]


@dataclass
class AnalysisResult:
    resolved_actions: list[ResolvedAction] = field(default_factory=list)
    ordering: list[str] = field(default_factory=list)
    temporal_cues: list[dict] = field(default_factory=list)
    conditions: list[dict] = field(default_factory=list)
    raw_parameters: list[dict] = field(default_factory=list)
    ambiguities: list[AmbiguityFlag] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)


def _resolve_entity_references(
    resolved_actions: list[ResolvedAction],
    entities: list[dict],
) -> None:
    output_map: dict[str, str] = {}
    for action in resolved_actions:
        obj = action.object.lower()
        output_map[obj] = action.step_id

    for i, action in enumerate(resolved_actions):
        if i == 0:
            continue
        obj = action.object.lower()
        for prev in resolved_actions[:i]:
            prev_obj = prev.object.lower()
            if obj in prev_obj or prev_obj in obj:
                action.inputs[f"from_{prev.step_id}"] = f"${{{prev.step_id}.output}}"
                break


def analyze(
    parse_result: ParseResult,
    registry: ActionRegistry | None = None,
    strict_mode: bool = False,
) -> AnalysisResult:
    if registry is None:
        registry = create_registry()

    result = AnalysisResult()

    for i, action in enumerate(parse_result.actions):
        step_id = f"step_{i + 1}"
        phrase = f"{action.verb} {action.object}".strip()
        catalog_action = registry.lookup(phrase)

        if catalog_action is None:
            catalog_action = registry.lookup(action.verb)

        resolved = ResolvedAction(
            step_id=step_id,
            catalog_action=catalog_action,
            verb=action.verb,
            object=action.object,
            original_text=action.original_text,
        )

        if catalog_action is None:
            result.ambiguities.append(AmbiguityFlag(
                text=action.original_text,
                options=[f"Could not resolve '{phrase}' to a known action"],
            ))
            if not strict_mode:
                result.assumptions.append(
                    f"Treating '{action.original_text}' as a generic action since no catalog match was found"
                )
        else:
            for out in catalog_action.outputs:
                resolved.outputs[out["name"]] = out["type"]

        result.resolved_actions.append(resolved)
        result.ordering.append(step_id)

    entities = [
        {"name": e.name, "type": e.type, "context": e.context}
        for e in parse_result.entities
    ]
    _resolve_entity_references(result.resolved_actions, entities)

    result.temporal_cues = [
        {"text": t.text, "type": t.type, "cron": t.cron}
        for t in parse_result.temporal_cues
    ]
    result.conditions = [
        {"text": c.text, "type": c.type, "expression": c.expression}
        for c in parse_result.conditions
    ]
    result.raw_parameters = [
        {"name": p.name, "value": p.value, "type": p.type}
        for p in parse_result.raw_parameters
    ]

    if len(result.resolved_actions) > 1 and not parse_result.conditions:
        result.assumptions.append(
            "Actions are assumed to execute sequentially in the order described"
        )

    return result
