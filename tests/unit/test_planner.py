import pytest

from src.catalog.registry import create_registry
from src.pipeline.parser import (
    ActionExtraction,
    Condition,
    ParseResult,
    RawParameter,
    TemporalCue,
)
from src.pipeline.analyzer import analyze, AmbiguityFlag, ResolvedAction, AnalysisResult
from src.pipeline.planner import plan, PlanResult


@pytest.fixture
def registry():
    return create_registry()


def build_analysis(registry, actions=None, temporal_cues=None, conditions=None, raw_parameters=None):
    pr = ParseResult(
        actions=actions or [],
        temporal_cues=temporal_cues or [],
        conditions=conditions or [],
        raw_parameters=raw_parameters or [],
    )
    return analyze(pr, registry=registry)


class TestDAGConstruction:
    def test_linear_chain_creates_dag(self, registry):
        analysis = build_analysis(registry, actions=[
            ActionExtraction(verb="pull", object="data", original_text="pull data"),
            ActionExtraction(verb="summarize", object="data", original_text="summarize it"),
            ActionExtraction(verb="email", object="report", original_text="email the report"),
        ])
        result = plan(analysis)
        assert set(result.dag.nodes) == {"step_1", "step_2", "step_3"}
        assert result.dag.get_dependencies("step_2") == ["step_1"]
        assert result.dag.get_dependencies("step_3") == ["step_2"]

    def test_single_step_no_edges(self, registry):
        analysis = build_analysis(registry, actions=[
            ActionExtraction(verb="notify", object="team", original_text="notify the team"),
        ])
        result = plan(analysis)
        assert len(result.dag.nodes) == 1
        assert len(result.dag.edges) == 0

    def test_dag_has_no_cycles(self, registry):
        analysis = build_analysis(registry, actions=[
            ActionExtraction(verb="pull", object="data", original_text="pull data"),
            ActionExtraction(verb="email", object="report", original_text="email it"),
        ])
        result = plan(analysis)
        assert result.dag.has_cycle() is False


class TestTriggerAssignment:
    def test_schedule_trigger_from_cron(self, registry):
        analysis = build_analysis(
            registry,
            actions=[ActionExtraction(verb="pull", object="data", original_text="pull data")],
            temporal_cues=[TemporalCue(text="every Monday", type="schedule", cron="0 9 * * 1")],
        )
        result = plan(analysis)
        assert result.trigger.type == "schedule"
        assert result.trigger.cron == "0 9 * * 1"

    def test_event_trigger_from_temporal_cue(self, registry):
        analysis = build_analysis(
            registry,
            actions=[ActionExtraction(verb="notify", object="oncall", original_text="notify oncall")],
            temporal_cues=[TemporalCue(text="when a file is uploaded", type="event")],
        )
        result = plan(analysis)
        assert result.trigger.type == "event"

    def test_manual_trigger_as_default(self, registry):
        analysis = build_analysis(
            registry,
            actions=[ActionExtraction(verb="pull", object="data", original_text="pull data")],
        )
        result = plan(analysis)
        assert result.trigger.type == "manual"

    def test_event_trigger_from_when_condition(self, registry):
        analysis = build_analysis(
            registry,
            actions=[ActionExtraction(verb="notify", object="oncall", original_text="notify oncall")],
            conditions=[Condition(text="when CPU > 90%", type="when", expression="cpu_usage > 90")],
        )
        result = plan(analysis)
        assert result.trigger.type == "event"
        assert result.trigger.event_type == "cpu_usage > 90"


class TestParameterExtraction:
    def test_parameters_extracted(self, registry):
        analysis = build_analysis(
            registry,
            actions=[ActionExtraction(verb="pull", object="data", original_text="pull data")],
            raw_parameters=[
                RawParameter(name="source", value="{source}", type="string"),
                RawParameter(name="threshold", value="90", type="number"),
            ],
        )
        result = plan(analysis)
        assert len(result.parameters) == 2
        names = {p.name for p in result.parameters}
        assert names == {"source", "threshold"}

    def test_no_parameters(self, registry):
        analysis = build_analysis(
            registry,
            actions=[ActionExtraction(verb="pull", object="data", original_text="pull data")],
        )
        result = plan(analysis)
        assert result.parameters == []


class TestErrorHandling:
    def test_default_error_handling(self, registry):
        analysis = build_analysis(
            registry,
            actions=[ActionExtraction(verb="pull", object="data", original_text="pull data")],
        )
        result = plan(analysis)
        assert result.error_handling.max_attempts == 3
        assert result.error_handling.backoff == "fixed"
        assert result.error_handling.on_failure == "stop"


class TestAssumptionsAndAmbiguities:
    def test_assumptions_carried_through(self, registry):
        analysis = build_analysis(registry, actions=[
            ActionExtraction(verb="pull", object="data", original_text="pull data"),
            ActionExtraction(verb="email", object="report", original_text="email it"),
        ])
        result = plan(analysis)
        assert any("sequentially" in a for a in result.assumptions)

    def test_ambiguities_carried_through(self, registry):
        analysis = build_analysis(registry, actions=[
            ActionExtraction(verb="dance", object="jig", original_text="dance a jig"),
        ])
        result = plan(analysis)
        assert len(result.ambiguities) == 1
