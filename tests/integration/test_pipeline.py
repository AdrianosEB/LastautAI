import json
from unittest.mock import MagicMock, patch

import pytest

from src.pipeline import generate_workflow, AmbiguityRejection, PipelineError


MOCK_SIMPLE_REPORT = {
    "actions": [
        {"verb": "pull", "object": "sales data", "original_text": "pull the latest sales data from our CRM"},
        {"verb": "summarize", "object": "sales data", "original_text": "summarize it"},
        {"verb": "email", "object": "report", "original_text": "email the report to the team"},
    ],
    "entities": [
        {"name": "CRM", "type": "source", "context": "data source"},
        {"name": "sales data", "type": "data", "context": "data to process"},
        {"name": "the team", "type": "person", "context": "email recipient"},
    ],
    "temporal_cues": [
        {"text": "Every Monday morning", "type": "schedule", "cron": "0 9 * * 1"},
    ],
    "conditions": [],
    "raw_parameters": [],
}

MOCK_CONDITIONAL = {
    "actions": [
        {"verb": "restart", "object": "service", "original_text": "restart the service"},
        {"verb": "notify", "object": "oncall", "original_text": "notify oncall"},
    ],
    "entities": [
        {"name": "service", "type": "service", "context": "service to restart"},
        {"name": "oncall", "type": "person", "context": "notification recipient"},
    ],
    "temporal_cues": [],
    "conditions": [
        {"text": "When CPU > 90%", "type": "when", "expression": "cpu_usage > 90"},
    ],
    "raw_parameters": [
        {"name": "threshold", "value": "90", "type": "number"},
    ],
}


def _mock_client(response_data):
    mock = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=json.dumps(response_data))]
    mock.messages.create.return_value = mock_resp
    return mock


class TestEndToEndPipeline:
    def test_simple_report_json(self):
        client = _mock_client(MOCK_SIMPLE_REPORT)
        result = generate_workflow(
            "Every Monday morning, pull the latest sales data from our CRM, summarize it, and email the report to the team",
            output_format="json",
            client=client,
        )
        assert isinstance(result, dict)
        assert result["trigger"]["type"] == "schedule"
        assert result["trigger"]["config"]["cron"] == "0 9 * * 1"
        assert len(result["steps"]) == 3
        assert result["steps"][0]["action"] == "fetch_data"
        assert result["steps"][1]["action"] == "transform_data"
        assert result["steps"][2]["action"] == "send_email"

    def test_simple_report_yaml(self):
        client = _mock_client(MOCK_SIMPLE_REPORT)
        result = generate_workflow(
            "Every Monday morning, pull the latest sales data",
            output_format="yaml",
            client=client,
        )
        assert isinstance(result, str)
        assert "trigger:" in result
        assert "schedule" in result

    def test_conditional_workflow(self):
        client = _mock_client(MOCK_CONDITIONAL)
        result = generate_workflow(
            "When CPU > 90%, restart the service and notify oncall",
            output_format="json",
            client=client,
        )
        assert result["trigger"]["type"] == "event"
        assert len(result["steps"]) == 2
        assert len(result["parameters"]) == 1
        assert result["parameters"][0]["name"] == "threshold"

    def test_strict_mode_ambiguity_rejection(self):
        ambiguous = {
            "actions": [{"verb": "dance", "object": "jig", "original_text": "dance a jig"}],
            "entities": [],
            "temporal_cues": [],
            "conditions": [],
            "raw_parameters": [],
        }
        client = _mock_client(ambiguous)
        with pytest.raises(AmbiguityRejection) as exc_info:
            generate_workflow("dance a jig", strict_mode=True, client=client)
        assert len(exc_info.value.ambiguities) > 0

    def test_non_strict_mode_assumes(self):
        ambiguous = {
            "actions": [{"verb": "dance", "object": "jig", "original_text": "dance a jig"}],
            "entities": [],
            "temporal_cues": [],
            "conditions": [],
            "raw_parameters": [],
        }
        client = _mock_client(ambiguous)
        result = generate_workflow("dance a jig", strict_mode=False, client=client)
        assert isinstance(result, dict)
        assert any("generic action" in a for a in result["assumptions"])

    def test_workflow_has_valid_structure(self):
        client = _mock_client(MOCK_SIMPLE_REPORT)
        result = generate_workflow("test", client=client)
        # All required top-level keys present
        assert "name" in result
        assert "trigger" in result
        assert "steps" in result
        assert "error_handling" in result
        # Each step has required fields
        for step in result["steps"]:
            assert "id" in step
            assert "action" in step
            assert "description" in step
            assert "dependencies" in step
