from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import anthropic


@dataclass
class ActionExtraction:
    verb: str
    object: str
    original_text: str


@dataclass
class EntityExtraction:
    name: str
    type: str  # source, destination, data, person, service, other
    context: str


@dataclass
class TemporalCue:
    text: str
    type: str  # schedule, delay, event, manual
    cron: str | None = None


@dataclass
class Condition:
    text: str
    type: str  # if, unless, when, otherwise
    expression: str


@dataclass
class RawParameter:
    name: str
    value: str
    type: str  # string, number, boolean, array


@dataclass
class ParseResult:
    actions: list[ActionExtraction] = field(default_factory=list)
    entities: list[EntityExtraction] = field(default_factory=list)
    temporal_cues: list[TemporalCue] = field(default_factory=list)
    conditions: list[Condition] = field(default_factory=list)
    raw_parameters: list[RawParameter] = field(default_factory=list)


PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text()


def _parse_llm_response(raw: str) -> dict:
    """Parse JSON from LLM response, stripping markdown fences if present."""
    text = raw.strip()
    if text.startswith("```"):
        # Remove opening fence (```json or ```)
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        # Remove closing fence
        if text.endswith("```"):
            text = text[:-3]
    return json.loads(text)


def _dict_to_parse_result(data: dict) -> ParseResult:
    """Convert the raw dict from the LLM into a typed ParseResult."""
    return ParseResult(
        actions=[
            ActionExtraction(
                verb=a.get("verb", ""),
                object=a.get("object", ""),
                original_text=a.get("original_text", ""),
            )
            for a in data.get("actions", [])
        ],
        entities=[
            EntityExtraction(
                name=e.get("name", ""),
                type=e.get("type", "other"),
                context=e.get("context", ""),
            )
            for e in data.get("entities", [])
        ],
        temporal_cues=[
            TemporalCue(
                text=t.get("text", ""),
                type=t.get("type", "manual"),
                cron=t.get("cron"),
            )
            for t in data.get("temporal_cues", [])
        ],
        conditions=[
            Condition(
                text=c.get("text", ""),
                type=c.get("type", "if"),
                expression=c.get("expression", ""),
            )
            for c in data.get("conditions", [])
        ],
        raw_parameters=[
            RawParameter(
                name=p.get("name", ""),
                value=p.get("value", ""),
                type=p.get("type", "string"),
            )
            for p in data.get("raw_parameters", [])
        ],
    )


def parse(description: str, client: anthropic.Anthropic | None = None) -> ParseResult:
    """Parse a natural language description into structured extraction data."""
    if client is None:
        client = anthropic.Anthropic()

    system_prompt = _load_prompt("system_prompt.txt")
    extraction_prompt = _load_prompt("extraction_prompt.txt").format(
        description=description,
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": extraction_prompt}],
    )

    raw_text = response.content[0].text
    data = _parse_llm_response(raw_text)
    return _dict_to_parse_result(data)
