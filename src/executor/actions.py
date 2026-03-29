"""Action executors — each action type gets a function that actually does the work."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable

import anthropic
import httpx

logger = logging.getLogger(__name__)

ExecutorFn = Callable[..., Any]


def execute_fetch_data(action: str, description: str, inputs: dict, context: dict) -> dict:
    """Fetch data from a URL or simulate fetching from a named source."""
    source = inputs.get("source", inputs.get("url", ""))

    # If it looks like a URL, make a real HTTP GET
    if source.startswith("http://") or source.startswith("https://"):
        logger.info("Fetching data from URL: %s", source)
        response = httpx.get(source, timeout=30)
        response.raise_for_status()
        try:
            return {"data": response.json(), "source": source, "status_code": response.status_code}
        except json.JSONDecodeError:
            return {"data": response.text, "source": source, "status_code": response.status_code}

    # Otherwise, use Claude to simulate/describe what this fetch would return
    logger.info("Simulating fetch from source: %s", source)
    return _ask_claude(
        f"Simulate fetching data for this step: '{description}'. "
        f"Source: {source}. "
        f"Return a realistic JSON sample of what this data would look like. "
        f"Return ONLY valid JSON, no explanation."
    )


def execute_transform_data(action: str, description: str, inputs: dict, context: dict) -> dict:
    """Transform data using Claude as the processing engine."""
    input_data = inputs.get("data", inputs.get("from_step_1", context))
    operation = inputs.get("operation", description)

    logger.info("Transforming data: %s", operation)
    return _ask_claude(
        f"You are a data transformation engine. "
        f"Perform this transformation: '{description}'. "
        f"Operation: {operation}. "
        f"Input data: {json.dumps(input_data) if isinstance(input_data, (dict, list)) else str(input_data)}. "
        f"Return the transformed result as valid JSON only, no explanation."
    )


def execute_send_email(action: str, description: str, inputs: dict, context: dict) -> dict:
    """Simulate sending an email (log it, return confirmation)."""
    to = inputs.get("to", "unknown")
    subject = inputs.get("subject", "No subject")
    body = inputs.get("body", "")

    if isinstance(body, (dict, list)):
        body = json.dumps(body, indent=2)

    logger.info("Sending email to: %s, subject: %s", to, subject)

    # In production, this would call SendGrid/SES/SMTP
    # For now, we log it and return success
    return {
        "sent": True,
        "to": to,
        "subject": subject,
        "body_preview": str(body)[:200],
        "note": "Email simulated — integrate with SendGrid/SES for real delivery",
    }


def execute_send_notification(action: str, description: str, inputs: dict, context: dict) -> dict:
    """Send a notification via webhook or simulate it."""
    channel = inputs.get("channel", "")
    message = inputs.get("message", description)

    if isinstance(message, (dict, list)):
        message = json.dumps(message, indent=2)

    # If channel looks like a webhook URL, actually POST to it
    if channel.startswith("http://") or channel.startswith("https://"):
        logger.info("Posting notification to webhook: %s", channel)
        response = httpx.post(channel, json={"text": str(message)}, timeout=30)
        return {"sent": True, "channel": channel, "status_code": response.status_code}

    logger.info("Notification to %s: %s", channel, str(message)[:100])
    return {
        "sent": True,
        "channel": channel,
        "message_preview": str(message)[:200],
        "note": "Notification simulated — provide a webhook URL for real delivery",
    }


def execute_write_file(action: str, description: str, inputs: dict, context: dict) -> dict:
    """Write content to a file."""
    path = inputs.get("path", "output.txt")
    content = inputs.get("content", "")

    if isinstance(content, (dict, list)):
        content = json.dumps(content, indent=2)

    logger.info("Writing file: %s", path)
    with open(path, "w") as f:
        f.write(str(content))

    return {"path": path, "bytes_written": len(str(content))}


def execute_http_request(action: str, description: str, inputs: dict, context: dict) -> dict:
    """Make a real HTTP request."""
    url = inputs.get("url", "")
    method = inputs.get("method", "GET").upper()
    body = inputs.get("body", None)

    if not url.startswith("http"):
        logger.info("Simulating HTTP %s to: %s", method, url)
        return _ask_claude(
            f"Simulate an HTTP {method} request to '{url}' for this step: '{description}'. "
            f"Return a realistic JSON response. Return ONLY valid JSON."
        )

    logger.info("HTTP %s %s", method, url)
    with httpx.Client(timeout=30) as client:
        if method == "GET":
            response = client.get(url)
        elif method == "POST":
            response = client.post(url, json=body if isinstance(body, dict) else None)
        elif method == "PUT":
            response = client.put(url, json=body if isinstance(body, dict) else None)
        elif method == "DELETE":
            response = client.delete(url)
        else:
            response = client.request(method, url)

    try:
        return {"response": response.json(), "status_code": response.status_code}
    except json.JSONDecodeError:
        return {"response": response.text, "status_code": response.status_code}


def execute_generic(action: str, description: str, inputs: dict, context: dict) -> dict:
    """Fallback executor — uses Claude to reason about and simulate the action."""
    logger.info("Generic executor for action: %s", action)
    return _ask_claude(
        f"You are executing a workflow step. "
        f"Action: {action}. "
        f"Description: {description}. "
        f"Inputs: {json.dumps(inputs)}. "
        f"Simulate executing this step and return a realistic JSON result. "
        f"Return ONLY valid JSON, no explanation."
    )


def _ask_claude(prompt: str) -> dict:
    """Call Claude to process/simulate a step."""
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()

    # Strip markdown fences
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"result": raw}


# Registry of action executors
_EXECUTORS: dict[str, ExecutorFn] = {
    "fetch_data": execute_fetch_data,
    "transform_data": execute_transform_data,
    "send_email": execute_send_email,
    "send_notification": execute_send_notification,
    "write_file": execute_write_file,
    "http_request": execute_http_request,
}


def get_executor(action: str) -> ExecutorFn:
    """Get the executor function for an action, falling back to generic."""
    return _EXECUTORS.get(action, execute_generic)
