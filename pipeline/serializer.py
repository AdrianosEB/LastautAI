from __future__ import annotations

import json
from pathlib import Path

import yaml
import jsonschema

from pipeline.graph.topological import topological_sort
from pipeline.planner import PlanResult


SCHEMA_PATH = Path(__file__).parent / "schemas" / "workflow.schema.json"


def _load_schema() -> dict:
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def serialize(plan_result: PlanResult, output_format: str = "json") -> dict | str:
    ordered_ids = topological_sort(plan_result.dag)

    steps = []
    for step_id in ordered_ids:
        metadata = plan_result.dag.get_node(step_id) or {}
        dependencies = plan_result.dag.get_dependencies(step_id)

        step = {
            "id": step_id,
            "action": metadata.get("catalog_action_id", metadata.get("action", metadata.get("verb", "unknown"))),
            "description": metadata.get("description", ""),
            "inputs": metadata.get("inputs", {}),
            "outputs": metadata.get("outputs", {}),
            "dependencies": dependencies,
        }

        for dep_id in dependencies:
            edge = plan_result.dag.get_edge(dep_id, step_id)
            if edge and edge.condition:
                step["conditions"] = {"if": edge.condition}
                break

        steps.append(step)

    trigger_config = {
        "cron": plan_result.trigger.cron,
        "event_type": plan_result.trigger.event_type,
        "webhook_path": plan_result.trigger.webhook_path,
    }

    workflow = {
        "name": _generate_name(plan_result),
        "trigger": {
            "type": plan_result.trigger.type,
            "config": trigger_config,
        },
        "steps": steps,
        "parameters": [
            {
                "name": p.name,
                "type": p.type,
                **({"default": p.default} if p.default is not None else {}),
                "description": p.description,
            }
            for p in plan_result.parameters
        ],
        "error_handling": {
            "default_retry": {
                "max_attempts": plan_result.error_handling.max_attempts,
                "backoff": plan_result.error_handling.backoff,
                "delay_seconds": plan_result.error_handling.delay_seconds,
            },
            "on_failure": plan_result.error_handling.on_failure,
            "step_overrides": plan_result.error_handling.step_overrides,
        },
        "assumptions": plan_result.assumptions,
    }

    schema = _load_schema()
    jsonschema.validate(instance=workflow, schema=schema)

    if output_format == "yaml":
        return yaml.dump(workflow, default_flow_style=False, sort_keys=False)
    return workflow


def _generate_name(plan_result: PlanResult) -> str:
    if plan_result.dag.nodes:
        first_node = plan_result.dag.nodes[0]
        metadata = plan_result.dag.get_node(first_node) or {}
        desc = metadata.get("description", "")
        if desc:
            name = desc.strip().rstrip(".")
            if len(name) > 60:
                name = name[:57] + "..."
            return name
    return "Untitled Workflow"
