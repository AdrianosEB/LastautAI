import json

import pytest
import yaml

from src.graph.dag import DAG
from src.pipeline.planner import PlanResult, TriggerPlan, ParameterPlan, ErrorHandlingPlan
from src.pipeline.serializer import serialize


def _make_plan_result(
    num_steps=2,
    trigger_type="manual",
    cron=None,
    parameters=None,
    conditions=None,
) -> PlanResult:
    dag = DAG()
    for i in range(1, num_steps + 1):
        dag.add_node(f"step_{i}", {
            "action": f"action_{i}",
            "catalog_action_id": f"action_{i}",
            "description": f"Do thing {i}",
            "verb": f"verb_{i}",
            "object": f"object_{i}",
            "inputs": {"source": "test"} if i == 1 else {f"from_step_{i-1}": f"${{step_{i-1}.output}}"},
            "outputs": {"result": "object"},
        })
    for i in range(1, num_steps):
        cond = conditions[i - 1] if conditions and i - 1 < len(conditions) else None
        dag.add_edge(f"step_{i}", f"step_{i + 1}", condition=cond)

    trigger = TriggerPlan(type=trigger_type, cron=cron)
    return PlanResult(
        dag=dag,
        trigger=trigger,
        parameters=parameters or [],
        error_handling=ErrorHandlingPlan(),
        assumptions=["Test assumption"],
    )


class TestJSONOutput:
    def test_produces_valid_dict(self):
        plan = _make_plan_result()
        result = serialize(plan, output_format="json")
        assert isinstance(result, dict)
        assert "name" in result
        assert "trigger" in result
        assert "steps" in result

    def test_steps_in_topological_order(self):
        plan = _make_plan_result(num_steps=3)
        result = serialize(plan, output_format="json")
        step_ids = [s["id"] for s in result["steps"]]
        assert step_ids == ["step_1", "step_2", "step_3"]

    def test_dependencies_populated(self):
        plan = _make_plan_result(num_steps=3)
        result = serialize(plan, output_format="json")
        assert result["steps"][0]["dependencies"] == []
        assert result["steps"][1]["dependencies"] == ["step_1"]
        assert result["steps"][2]["dependencies"] == ["step_2"]

    def test_trigger_type_set(self):
        plan = _make_plan_result(trigger_type="schedule", cron="0 9 * * 1")
        result = serialize(plan, output_format="json")
        assert result["trigger"]["type"] == "schedule"
        assert result["trigger"]["config"]["cron"] == "0 9 * * 1"

    def test_manual_trigger_default(self):
        plan = _make_plan_result()
        result = serialize(plan, output_format="json")
        assert result["trigger"]["type"] == "manual"

    def test_parameters_included(self):
        params = [ParameterPlan(name="source", type="string", default="CRM", description="Data source")]
        plan = _make_plan_result(parameters=params)
        result = serialize(plan, output_format="json")
        assert len(result["parameters"]) == 1
        assert result["parameters"][0]["name"] == "source"

    def test_error_handling_defaults(self):
        plan = _make_plan_result()
        result = serialize(plan, output_format="json")
        eh = result["error_handling"]
        assert eh["default_retry"]["max_attempts"] == 3
        assert eh["on_failure"] == "stop"

    def test_assumptions_included(self):
        plan = _make_plan_result()
        result = serialize(plan, output_format="json")
        assert "Test assumption" in result["assumptions"]

    def test_conditional_edge_produces_conditions(self):
        plan = _make_plan_result(num_steps=2, conditions=["x > 10"])
        result = serialize(plan, output_format="json")
        assert result["steps"][1].get("conditions") == {"if": "x > 10"}


class TestYAMLOutput:
    def test_produces_yaml_string(self):
        plan = _make_plan_result()
        result = serialize(plan, output_format="yaml")
        assert isinstance(result, str)

    def test_yaml_is_parseable(self):
        plan = _make_plan_result()
        result = serialize(plan, output_format="yaml")
        parsed = yaml.safe_load(result)
        assert parsed["trigger"]["type"] == "manual"
        assert len(parsed["steps"]) == 2

    def test_yaml_roundtrip_matches_json(self):
        plan = _make_plan_result(num_steps=3, trigger_type="schedule", cron="0 6 * * *")
        json_result = serialize(plan, output_format="json")
        yaml_result = serialize(plan, output_format="yaml")
        yaml_parsed = yaml.safe_load(yaml_result)
        assert json_result == yaml_parsed


class TestSchemaValidation:
    def test_valid_workflow_passes(self):
        plan = _make_plan_result()
        # Should not raise
        serialize(plan, output_format="json")

    def test_single_step_valid(self):
        plan = _make_plan_result(num_steps=1)
        result = serialize(plan, output_format="json")
        assert len(result["steps"]) == 1
