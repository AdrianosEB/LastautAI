"""Shared utilities for parsing LLM responses."""

import json


def strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) from LLM output."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def parse_json_response(raw: str) -> dict:
    """Parse JSON from an LLM response, stripping markdown fences if present.

    Returns the parsed dict on success, or {"result": raw_text} if JSON parsing fails.
    """
    text = strip_markdown_fences(raw)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"result": text}
