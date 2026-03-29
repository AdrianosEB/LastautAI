"""
AI-powered workflow execution — Claude uses tools to run workflows step by step.
Streams progress back to the frontend via SSE.
"""

import json
import logging
import os

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.api.routes.auth import get_current_user
from src.db.models import User
from src.utils.ai_client import get_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflows", tags=["execute-ai"])

TOOLS = [
    {
        "name": "fetch_url",
        "description": "Fetch data from a URL. Use this to read web pages, call APIs, or download data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch"},
                "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"], "description": "HTTP method"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "send_slack_message",
        "description": "Send a message to a Slack channel.",
        "input_schema": {
            "type": "object",
            "properties": {
                "channel": {"type": "string", "description": "Slack channel name (e.g. #general)"},
                "message": {"type": "string", "description": "The message text to send"},
            },
            "required": ["channel", "message"],
        },
    },
    {
        "name": "send_email",
        "description": "Send an email to a recipient.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body content"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "transform_data",
        "description": "Transform, filter, or format data. Use this for any data processing step.",
        "input_schema": {
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "The input data to transform (JSON string)"},
                "instruction": {"type": "string", "description": "What transformation to apply"},
            },
            "required": ["data", "instruction"],
        },
    },
    {
        "name": "create_document",
        "description": "Create a document, report, or summary.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Document title"},
                "content": {"type": "string", "description": "Document content"},
                "format": {"type": "string", "enum": ["text", "markdown", "html"], "description": "Output format"},
            },
            "required": ["title", "content"],
        },
    },
    {
        "name": "log_result",
        "description": "Log the final result or output of the workflow.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "The final result message"},
            },
            "required": ["message"],
        },
    },
]


def _execute_tool(name: str, inputs: dict) -> dict:
    """Actually execute a tool and return the result."""

    if name == "fetch_url":
        url = inputs.get("url", "")
        method = inputs.get("method", "GET").upper()
        if not url.startswith("http"):
            return {"error": f"Invalid URL: {url}"}
        try:
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                resp = client.request(method, url)
                try:
                    data = resp.json()
                except Exception:
                    data = resp.text[:2000]
                return {"status_code": resp.status_code, "data": data}
        except Exception as e:
            return {"error": str(e)}

    elif name == "send_slack_message":
        webhook = os.getenv("SLACK_WEBHOOK_URL", "")
        channel = inputs.get("channel", "#general")
        message = inputs.get("message", "")
        if webhook:
            try:
                resp = httpx.post(webhook, json={"text": f"[{channel}] {message}"}, timeout=10)
                return {"sent": True, "channel": channel, "status_code": resp.status_code}
            except Exception as e:
                return {"sent": False, "error": str(e)}
        return {"sent": True, "simulated": True, "channel": channel, "message_preview": message[:200]}

    elif name == "send_email":
        to = inputs.get("to", "")
        subject = inputs.get("subject", "")
        body = inputs.get("body", "")
        logger.info("Email (simulated) to=%s subject=%s", to, subject)
        return {
            "delivered": True,
            "simulated": True,
            "to": to,
            "subject": subject,
            "body_preview": body[:300],
            "note": "Email logged locally. Connect SendGrid/SES for real delivery.",
        }

    elif name == "transform_data":
        data = inputs.get("data", "")
        instruction = inputs.get("instruction", "")
        try:
            resp = get_client().messages.create(
                model="claude-haiku-4-5",
                max_tokens=1024,
                messages=[{"role": "user", "content": (
                    f"Transform this data according to the instruction.\n\n"
                    f"Data: {data}\n\nInstruction: {instruction}\n\n"
                    f"Return ONLY the transformed result as valid JSON. No explanation."
                )}],
            )
            raw = next((b.text for b in resp.content if b.type == "text"), "")
            try:
                return {"transformed": True, "result": json.loads(raw)}
            except json.JSONDecodeError:
                return {"transformed": True, "result": raw.strip()}
        except Exception as e:
            return {"transformed": False, "error": str(e)}

    elif name == "create_document":
        title = inputs.get("title", "Untitled")
        content = inputs.get("content", "")
        fmt = inputs.get("format", "text")
        return {
            "created": True,
            "title": title,
            "format": fmt,
            "content_length": len(content),
            "content_preview": content[:500],
        }

    elif name == "log_result":
        return {"logged": True, "message": inputs.get("message", "")}

    return {"error": f"Unknown tool: {name}"}


class ExecuteAIRequest(BaseModel):
    description: str
    workflow: dict | None = None


@router.post("/execute-ai")
def execute_ai(
    req: ExecuteAIRequest,
    user: User = Depends(get_current_user),
):
    def event_stream():
        workflow_context = ""
        if req.workflow:
            workflow_context = f"\n\nHere is the structured workflow definition for reference:\n{json.dumps(req.workflow, indent=2)}"

        system_prompt = (
            "You are a workflow execution engine. Your job is to execute the described workflow "
            "step by step using the tools provided. For each step:\n"
            "1. Briefly state what you're about to do\n"
            "2. Call the appropriate tool\n"
            "3. After getting the result, briefly state what happened\n"
            "4. Move to the next step\n\n"
            "IMPORTANT: Each tool call receives the result from the previous step. "
            "Use data from earlier steps to feed into later steps. For example, if step 1 "
            "fetches data, use that data in step 2's transform or message.\n\n"
            "Execute all steps in logical order. Use real URLs and data when available. "
            "When you're done with all steps, summarize what was accomplished.\n"
            "Be concise — one sentence per explanation, then call the tool."
        )

        # Track step results for inter-step chaining
        step_outputs = []

        user_msg = f"Execute this workflow:\n\n{req.description}{workflow_context}"

        messages = [{"role": "user", "content": user_msg}]

        max_iterations = 15
        client = get_client()

        for _ in range(max_iterations):
            try:
                response = client.messages.create(
                    model="claude-haiku-4-5",
                    max_tokens=4096,
                    system=system_prompt,
                    tools=TOOLS,
                    messages=messages,
                )
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                break

            # Build the full assistant content first
            assistant_content = []
            tool_results = []

            for block in response.content:
                if block.type == "text" and block.text.strip():
                    yield f"data: {json.dumps({'type': 'thinking', 'text': block.text.strip()})}\n\n"
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

                    step_num = len(step_outputs) + 1
                    yield f"data: {json.dumps({'type': 'step_start', 'tool': block.name, 'input': block.input, 'step': step_num})}\n\n"

                    result = _execute_tool(block.name, block.input)

                    # Track for inter-step chaining
                    step_outputs.append({"step": step_num, "tool": block.name, "result": result})

                    yield f"data: {json.dumps({'type': 'step_complete', 'tool': block.name, 'result': result, 'step': step_num})}\n\n"

                    # Include chain context so Claude knows previous step results
                    chain_note = ""
                    if len(step_outputs) > 1:
                        prev = step_outputs[-2]
                        chain_note = f"\n\n[Previous step {prev['step']} ({prev['tool']}) returned: {json.dumps(prev['result'])[:500]}]"

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result) + chain_note,
                    })

            # Add assistant message + all tool results as one exchange
            messages.append({"role": "assistant", "content": assistant_content})
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            if response.stop_reason == "end_turn":
                yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                break

        else:
            yield f"data: {json.dumps({'type': 'complete', 'message': 'Max steps reached'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
