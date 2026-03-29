import logging
import uuid

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/n8n")


class DeployRequest(BaseModel):
    n8n_url: str
    api_key: str
    workflow: dict


def _ensure_node_ids(workflow: dict) -> dict:
    """Ensure every node has a unique UUID id field, which n8n requires."""
    for node in workflow.get("nodes", []):
        if "id" not in node:
            node["id"] = str(uuid.uuid4())
    return workflow


@router.post("/deploy")
async def deploy_to_n8n(request: DeployRequest):
    """Proxy the workflow to an n8n instance via its REST API."""
    url = request.n8n_url.rstrip("/") + "/api/v1/workflows"

    workflow = _ensure_node_ids(request.workflow)

    logger.info("Deploying to n8n at %s", url)
    logger.info("Workflow payload: %s", workflow)

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                url,
                json=workflow,
                headers={
                    "X-N8N-API-KEY": request.api_key,
                    "Content-Type": "application/json",
                },
            )

        data = resp.json()
        logger.info("n8n response status=%d body=%s", resp.status_code, data)

        if resp.status_code in (200, 201):
            return {
                "id": data.get("id"),
                "name": data.get("name"),
                "active": data.get("active", False),
                "url": f"{request.n8n_url.rstrip('/')}/workflow/{data.get('id')}",
            }
        else:
            return JSONResponse(
                status_code=resp.status_code,
                content={
                    "error": data.get("message", "n8n API error"),
                    "details": data,
                },
            )

    except httpx.ConnectError:
        return JSONResponse(
            status_code=502,
            content={"error": f"Cannot connect to n8n at {request.n8n_url}. Is it running?"},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )
