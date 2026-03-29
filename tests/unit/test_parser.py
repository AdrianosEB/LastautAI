import json
from unittest.mock import MagicMock, patch

import pytest

from src.pipeline.parser import (
    ParseResult,
    _dict_to_parse_result,
    _parse_llm_response,
    parse,
)


SAMPLE_LLM_RESPONSE = {
    "actions": [
        {"verb": "pull", "object": "sales data", "original_text": "pull the latest sales data from our CRM"},
        {"verb": "summarize", "object": "sales data", "original_text": "summarize it"},
        {"verb": "email", "object": "report", "original_text": "email the report to the team"},
    ],
    "entities": [
        {"name": "CRM", "type": "source", "context": "data source for sales data"},
        {"name": "sales data", "type": "data", "context": "data to be pulled and summarized"},
        {"name": "the team", "type": "person", "context": "email recipient"},
    ],
    "temporal_cues": [
        {"text": "Every Monday morning", "type": "schedule", "cron": "0 9 * * 1"},
    ],
    "conditions": [],
    "raw_parameters": [],
}


class TestParseLlmResponse:
    def test_plain_json(self):
        result = _parse_llm_response(json.dumps({"actions": []}))
        assert result == {"actions": []}

    def test_json_with_markdown_fence(self):
        text = '```json\n{"actions": []}\n```'
        result = _parse_llm_response(text)
        assert result == {"actions": []}

    def test_json_with_bare_fence(self):
        text = '```\n{"actions": []}\n```'
        result = _parse_llm_response(text)
        assert result == {"actions": []}

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_llm_response("not json at all")


class TestDictToParseResult:
    def test_full_conversion(self):
        result = _dict_to_parse_result(SAMPLE_LLM_RESPONSE)
        assert isinstance(result, ParseResult)
        assert len(result.actions) == 3
        assert result.actions[0].verb == "pull"
        assert len(result.entities) == 3
        assert len(result.temporal_cues) == 1
        assert result.temporal_cues[0].cron == "0 9 * * 1"
        assert len(result.conditions) == 0
        assert len(result.raw_parameters) == 0

    def test_empty_dict(self):
        result = _dict_to_parse_result({})
        assert result.actions == []
        assert result.entities == []
        assert result.temporal_cues == []

    def test_missing_fields_use_defaults(self):
        data = {"actions": [{"verb": "send"}]}
        result = _dict_to_parse_result(data)
        assert result.actions[0].object == ""
        assert result.actions[0].original_text == ""


class TestParse:
    def test_parse_calls_claude_and_returns_result(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(SAMPLE_LLM_RESPONSE))]
        mock_client.messages.create.return_value = mock_response

        result = parse("Every Monday morning, pull sales data and email the team", client=mock_client)

        assert isinstance(result, ParseResult)
        assert len(result.actions) == 3
        assert result.actions[0].verb == "pull"
        assert result.temporal_cues[0].type == "schedule"
        mock_client.messages.create.assert_called_once()

    def test_parse_handles_fenced_response(self):
        mock_client = MagicMock()
        fenced = '```json\n' + json.dumps(SAMPLE_LLM_RESPONSE) + '\n```'
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=fenced)]
        mock_client.messages.create.return_value = mock_response

        result = parse("test description", client=mock_client)
        assert len(result.actions) == 3

    def test_parse_raises_on_malformed_response(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="This is not JSON")]
        mock_client.messages.create.return_value = mock_response

        with pytest.raises(json.JSONDecodeError):
            parse("test description", client=mock_client)
