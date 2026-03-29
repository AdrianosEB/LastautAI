"""Pipeline orchestrator — chains parser → analyzer → planner → serializer."""

from __future__ import annotations

import logging
import time
from typing import Any

import anthropic

from pipeline.catalog.registry import create_registry
from pipeline.parser import parse
from pipeline.analyzer import analyze
from pipeline.planner import plan
from pipeline.serializer import serialize

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    def __init__(self, stage: str, message: str):
        self.stage = stage
        self.message = message
        super().__init__(f"[{stage}] {message}")


class AmbiguityRejection(Exception):
    def __init__(self, ambiguities: list[dict]):
        self.ambiguities = ambiguities
        super().__init__("Input is ambiguous and strict_mode is enabled")


def generate_workflow(
    description: str,
    output_format: str = "json",
    strict_mode: bool = False,
    client: anthropic.Anthropic | None = None,
) -> dict | str:
    pipeline_start = time.monotonic()

    try:
        logger.info("Parser: starting extraction")
        t0 = time.monotonic()
        parse_result = parse(description, client=client)
        logger.info("Parser: completed in %.3fs, extracted %d actions", time.monotonic() - t0, len(parse_result.actions))
    except Exception as e:
        raise PipelineError("parser", str(e)) from e

    try:
        logger.info("Analyzer: starting analysis")
        t0 = time.monotonic()
        registry = create_registry()
        analysis_result = analyze(parse_result, registry=registry, strict_mode=strict_mode)
        logger.info("Analyzer: completed in %.3fs, %d ambiguities, %d assumptions",
                    time.monotonic() - t0, len(analysis_result.ambiguities), len(analysis_result.assumptions))
    except Exception as e:
        raise PipelineError("analyzer", str(e)) from e

    if strict_mode and analysis_result.ambiguities:
        raise AmbiguityRejection([
            {"text": a.text, "options": a.options}
            for a in analysis_result.ambiguities
        ])

    try:
        logger.info("Planner: building DAG")
        t0 = time.monotonic()
        plan_result = plan(analysis_result)
        logger.info("Planner: completed in %.3fs, %d nodes, trigger=%s",
                    time.monotonic() - t0, len(plan_result.dag.nodes), plan_result.trigger.type)
    except Exception as e:
        raise PipelineError("planner", str(e)) from e

    try:
        logger.info("Serializer: producing %s output", output_format)
        t0 = time.monotonic()
        result = serialize(plan_result, output_format=output_format)
        logger.info("Serializer: completed in %.3fs", time.monotonic() - t0)
    except Exception as e:
        raise PipelineError("serializer", str(e)) from e

    logger.info("Pipeline: total time %.3fs", time.monotonic() - pipeline_start)
    return result


def generate_workflow_steps(
    description: str,
    output_format: str = "json",
    strict_mode: bool = False,
    client: anthropic.Anthropic | None = None,
) -> dict[str, Any]:
    import dataclasses

    def _dc_to_dict(obj: Any) -> Any:
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return {k: _dc_to_dict(v) for k, v in dataclasses.asdict(obj).items()}
        if isinstance(obj, list):
            return [_dc_to_dict(i) for i in obj]
        if isinstance(obj, dict):
            return {k: _dc_to_dict(v) for k, v in obj.items()}
        return obj

    stages: dict[str, Any] = {}

    try:
        t0 = time.monotonic()
        parse_result = parse(description, client=client)
        stages["parser"] = {
            "status": "success",
            "duration_ms": round((time.monotonic() - t0) * 1000),
            "result": _dc_to_dict(parse_result),
        }
    except Exception as e:
        stages["parser"] = {"status": "error", "error": str(e)}
        return stages

    try:
        t0 = time.monotonic()
        registry = create_registry()
        analysis_result = analyze(parse_result, registry=registry, strict_mode=strict_mode)
        stages["analyzer"] = {
            "status": "success",
            "duration_ms": round((time.monotonic() - t0) * 1000),
            "result": _dc_to_dict(analysis_result),
        }
    except Exception as e:
        stages["analyzer"] = {"status": "error", "error": str(e)}
        return stages

    if strict_mode and analysis_result.ambiguities:
        stages["analyzer"]["ambiguities"] = [
            {"text": a.text, "options": a.options}
            for a in analysis_result.ambiguities
        ]
        stages["analyzer"]["status"] = "ambiguous"
        return stages

    try:
        t0 = time.monotonic()
        plan_result = plan(analysis_result)
        dag_summary = {
            "nodes": plan_result.dag.nodes,
            "edges": [{"from": e.source, "to": e.target} for e in plan_result.dag.edges],
        }
        stages["planner"] = {
            "status": "success",
            "duration_ms": round((time.monotonic() - t0) * 1000),
            "result": {
                "dag": dag_summary,
                "trigger": _dc_to_dict(plan_result.trigger),
                "parameters": _dc_to_dict(plan_result.parameters),
                "error_handling": _dc_to_dict(plan_result.error_handling),
                "assumptions": plan_result.assumptions,
            },
        }
    except Exception as e:
        stages["planner"] = {"status": "error", "error": str(e)}
        return stages

    try:
        t0 = time.monotonic()
        result = serialize(plan_result, output_format=output_format)
        stages["serializer"] = {
            "status": "success",
            "duration_ms": round((time.monotonic() - t0) * 1000),
        }
        stages["workflow"] = result
    except Exception as e:
        stages["serializer"] = {"status": "error", "error": str(e)}
        return stages

    return stages
