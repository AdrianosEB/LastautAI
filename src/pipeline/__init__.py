"""Pipeline orchestrator — chains parser → analyzer → planner → serializer."""

from __future__ import annotations

import logging
import time
from typing import Any

import anthropic

from src.catalog.registry import create_registry
from src.pipeline.parser import parse
from src.pipeline.analyzer import analyze
from src.pipeline.planner import plan
from src.pipeline.serializer import serialize

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Raised when a pipeline stage fails."""
    def __init__(self, stage: str, message: str):
        self.stage = stage
        self.message = message
        super().__init__(f"[{stage}] {message}")


class AmbiguityRejection(Exception):
    """Raised when strict_mode is on and input is ambiguous."""
    def __init__(self, ambiguities: list[dict]):
        self.ambiguities = ambiguities
        super().__init__("Input is ambiguous and strict_mode is enabled")


def generate_workflow(
    description: str,
    output_format: str = "json",
    strict_mode: bool = False,
    client: anthropic.Anthropic | None = None,
) -> dict | str:
    """
    Full pipeline: NL description → structured workflow definition.

    Returns a dict (JSON) or string (YAML) depending on output_format.
    Raises AmbiguityRejection if strict_mode=True and input is ambiguous.
    Raises PipelineError on any stage failure.
    """
    pipeline_start = time.monotonic()

    # Stage 1: Parse
    try:
        logger.info("Parser: starting extraction")
        t0 = time.monotonic()
        parse_result = parse(description, client=client)
        logger.info("Parser: completed in %.3fs, extracted %d actions", time.monotonic() - t0, len(parse_result.actions))
    except Exception as e:
        raise PipelineError("parser", str(e)) from e

    # Stage 2: Analyze
    try:
        logger.info("Analyzer: starting analysis")
        t0 = time.monotonic()
        registry = create_registry()
        analysis_result = analyze(parse_result, registry=registry, strict_mode=strict_mode)
        logger.info("Analyzer: completed in %.3fs, %d ambiguities, %d assumptions",
                     time.monotonic() - t0, len(analysis_result.ambiguities), len(analysis_result.assumptions))
    except Exception as e:
        raise PipelineError("analyzer", str(e)) from e

    # Check for ambiguities in strict mode
    if strict_mode and analysis_result.ambiguities:
        logger.warning("Rejecting ambiguous input: %d ambiguities found", len(analysis_result.ambiguities))
        raise AmbiguityRejection([
            {"text": a.text, "options": a.options}
            for a in analysis_result.ambiguities
        ])

    # Stage 3: Plan
    try:
        logger.info("Planner: building DAG")
        t0 = time.monotonic()
        plan_result = plan(analysis_result)
        logger.info("Planner: completed in %.3fs, %d nodes, trigger=%s",
                     time.monotonic() - t0, len(plan_result.dag.nodes), plan_result.trigger.type)
    except Exception as e:
        raise PipelineError("planner", str(e)) from e

    # Stage 4: Serialize
    try:
        logger.info("Serializer: producing %s output", output_format)
        t0 = time.monotonic()
        result = serialize(plan_result, output_format=output_format)
        logger.info("Serializer: completed in %.3fs", time.monotonic() - t0)
    except Exception as e:
        raise PipelineError("serializer", str(e)) from e

    logger.info("Pipeline: total time %.3fs", time.monotonic() - pipeline_start)
    return result
