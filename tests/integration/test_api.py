import json
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

from src.api.server import app


MOCK_LLM_RESPONSE = {
    "actions": [
        {"verb": "pull", "object": "sales data", "original_text": "pull the latest sales data from our CRM"},
        {"verb": "summarize", "object": "sales data", "original_text": "summarize it"},
        {"verb": "email", "object": "report", "original_text": "email the report to the team"},
    ],
    "entities": [
        {"name": "CRM", "type": "source", "context": "data source"},
        {"name": "sales data", "type": "data", "context": "data to process"},
        {"name": "the team", "type": "person", "context": "recipient"},
    ],
    "temporal_cues": [
        {"text": "Every Monday morning", "type": "schedule", "cron": "0 9 * * 1"},
    ],
    "conditions": [],
    "raw_parameters": [],
}

MOCK_AMBIGUOUS_RESPONSE = {
    "actions": [
        {"verb": "dance", "object": "jig", "original_text": "dance a jig for the boss"},
    ],
    "entities": [],
    "temporal_cues": [],
    "conditions": [],
    "raw_parameters": [],
}


def _mock_claude_client(response_data):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps(response_data))]
    mock_client.messages.create.return_value = mock_response
    return mock_client


@pytest.fixture
def transport():
    return ASGITransport(app=app)


@pytest.mark.asyncio
async def test_health_check(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_generate_success(transport):
    mock_client = _mock_claude_client(MOCK_LLM_RESPONSE)
    with patch("src.pipeline.parser.anthropic.Anthropic", return_value=mock_client):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/workflows/generate", json={
                "description": "Every Monday morning, pull sales data and email the team",
            })
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "trigger" in data
    assert data["trigger"]["type"] == "schedule"
    assert len(data["steps"]) == 3


@pytest.mark.asyncio
async def test_generate_yaml(transport):
    mock_client = _mock_claude_client(MOCK_LLM_RESPONSE)
    with patch("src.pipeline.parser.anthropic.Anthropic", return_value=mock_client):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/workflows/generate", json={
                "description": "Every Monday, pull sales data and email team",
                "output_format": "yaml",
            })
    assert response.status_code == 200
    assert "text/yaml" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_generate_strict_mode_rejects_ambiguous(transport):
    mock_client = _mock_claude_client(MOCK_AMBIGUOUS_RESPONSE)
    with patch("src.pipeline.parser.anthropic.Anthropic", return_value=mock_client):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/workflows/generate", json={
                "description": "dance a jig for the boss",
                "strict_mode": True,
            })
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "ambiguous_input"
    assert len(data["ambiguities"]) > 0


@pytest.mark.asyncio
async def test_validate_pass(transport):
    valid_workflow = {
        "name": "Test Workflow",
        "trigger": {"type": "manual", "config": {"cron": None, "event_type": None, "webhook_path": None}},
        "steps": [
            {"id": "step_1", "action": "fetch_data", "description": "Fetch data"}
        ],
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/workflows/validate", json={"workflow": valid_workflow})
    assert response.status_code == 200
    assert response.json()["valid"] is True


@pytest.mark.asyncio
async def test_validate_failure(transport):
    invalid_workflow = {
        "name": "Bad Workflow",
        "trigger": {"type": "invalid_type", "config": {}},
        "steps": [
            {"id": "step_1", "action": "fetch_data", "description": "Fetch data"}
        ],
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/workflows/validate", json={"workflow": invalid_workflow})
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert len(data["errors"]) > 0


@pytest.mark.asyncio
async def test_generate_empty_description_rejected(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/workflows/generate", json={"description": ""})
    assert response.status_code == 422
