"""
Golden test suite: runs each example input through the pipeline (with mocked LLM)
and validates that the output has the correct structure and key properties.

Since LLM outputs are non-deterministic, golden tests validate structural
correctness rather than exact output matching.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import jsonschema

from src.pipeline import generate_workflow


EXAMPLES_DIR = Path(__file__).parent.parent.parent / "examples"
INPUTS_DIR = EXAMPLES_DIR / "inputs"
OUTPUTS_DIR = EXAMPLES_DIR / "outputs"
SCHEMA_PATH = Path(__file__).parent.parent.parent / "schemas" / "workflow.schema.json"


def _load_schema():
    with open(SCHEMA_PATH) as f:
        return json.load(f)


# Map each example to a mock LLM response that simulates what Claude would return
MOCK_RESPONSES = {
    "simple_report": {
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
        "temporal_cues": [{"text": "Every Monday morning", "type": "schedule", "cron": "0 9 * * 1"}],
        "conditions": [],
        "raw_parameters": [],
    },
    "conditional_alert": {
        "actions": [
            {"verb": "restart", "object": "service", "original_text": "restart the service"},
            {"verb": "notify", "object": "oncall engineer", "original_text": "notify the oncall engineer"},
        ],
        "entities": [
            {"name": "service", "type": "service", "context": "service to restart"},
            {"name": "oncall engineer", "type": "person", "context": "notification target"},
        ],
        "temporal_cues": [],
        "conditions": [{"text": "When CPU usage exceeds 90%", "type": "when", "expression": "cpu_usage > 90"}],
        "raw_parameters": [{"name": "threshold", "value": "90", "type": "number"}],
    },
    "multi_step_pipeline": {
        "actions": [
            {"verb": "fetch", "object": "logs", "original_text": "fetch the latest logs from the server"},
            {"verb": "filter", "object": "errors", "original_text": "filter for errors"},
            {"verb": "summarize", "object": "findings", "original_text": "summarize the findings"},
            {"verb": "post", "object": "summary", "original_text": "post the summary to the Slack #alerts channel"},
        ],
        "entities": [
            {"name": "server", "type": "source", "context": "log source"},
            {"name": "Slack #alerts", "type": "destination", "context": "notification channel"},
        ],
        "temporal_cues": [],
        "conditions": [],
        "raw_parameters": [],
    },
    "webhook_trigger": {
        "actions": [
            {"verb": "validate", "object": "order data", "original_text": "validate the order data"},
            {"verb": "update", "object": "inventory", "original_text": "update the inventory system"},
            {"verb": "send", "object": "confirmation email", "original_text": "send a confirmation email to the customer"},
        ],
        "entities": [
            {"name": "order", "type": "data", "context": "incoming order"},
            {"name": "inventory system", "type": "service", "context": "system to update"},
            {"name": "customer", "type": "person", "context": "email recipient"},
        ],
        "temporal_cues": [{"text": "When a new order comes in via webhook", "type": "event"}],
        "conditions": [],
        "raw_parameters": [],
    },
    "parameterized_etl": {
        "actions": [
            {"verb": "pull", "object": "data", "original_text": "pull data from {source}"},
            {"verb": "transform", "object": "data", "original_text": "transform it using the standard cleanup rules"},
            {"verb": "load", "object": "results", "original_text": "load the results into {destination}"},
        ],
        "entities": [
            {"name": "{source}", "type": "source", "context": "data source parameter"},
            {"name": "{destination}", "type": "destination", "context": "data destination parameter"},
        ],
        "temporal_cues": [{"text": "Daily at 6am", "type": "schedule", "cron": "0 6 * * *"}],
        "conditions": [],
        "raw_parameters": [
            {"name": "source", "value": "{source}", "type": "string"},
            {"name": "destination", "value": "{destination}", "type": "string"},
        ],
    },
}


def _mock_client(response_data):
    mock = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=json.dumps(response_data))]
    mock.messages.create.return_value = mock_resp
    return mock


def discover_examples():
    """Discover all input/output example pairs."""
    pairs = []
    for input_file in sorted(INPUTS_DIR.glob("*.txt")):
        name = input_file.stem
        output_file = OUTPUTS_DIR / f"{name}.json"
        if output_file.exists():
            pairs.append((name, input_file, output_file))
    return pairs


EXAMPLE_PAIRS = discover_examples()


@pytest.mark.parametrize(
    "name,input_file,output_file",
    EXAMPLE_PAIRS,
    ids=[p[0] for p in EXAMPLE_PAIRS],
)
class TestGolden:
    def test_output_is_valid_against_schema(self, name, input_file, output_file):
        """Generated output must validate against the workflow JSON schema."""
        if name not in MOCK_RESPONSES:
            pytest.skip(f"No mock response configured for {name}")

        description = input_file.read_text().strip()
        client = _mock_client(MOCK_RESPONSES[name])
        result = generate_workflow(description, output_format="json", client=client)

        schema = _load_schema()
        jsonschema.validate(instance=result, schema=schema)

    def test_output_has_correct_step_count(self, name, input_file, output_file):
        """Step count should match the expected output."""
        if name not in MOCK_RESPONSES:
            pytest.skip(f"No mock response configured for {name}")

        expected = json.loads(output_file.read_text())
        description = input_file.read_text().strip()
        client = _mock_client(MOCK_RESPONSES[name])
        result = generate_workflow(description, output_format="json", client=client)

        assert len(result["steps"]) == len(expected["steps"])

    def test_output_has_correct_trigger_type(self, name, input_file, output_file):
        """Trigger type should match the expected output."""
        if name not in MOCK_RESPONSES:
            pytest.skip(f"No mock response configured for {name}")

        expected = json.loads(output_file.read_text())
        description = input_file.read_text().strip()
        client = _mock_client(MOCK_RESPONSES[name])
        result = generate_workflow(description, output_format="json", client=client)

        assert result["trigger"]["type"] == expected["trigger"]["type"]

    def test_expected_output_is_valid_against_schema(self, name, input_file, output_file):
        """The hand-crafted expected output must also be schema-valid."""
        expected = json.loads(output_file.read_text())
        schema = _load_schema()
        jsonschema.validate(instance=expected, schema=schema)
