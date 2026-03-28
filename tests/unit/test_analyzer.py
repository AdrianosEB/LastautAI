import pytest

from src.catalog.registry import create_registry
from src.pipeline.parser import (
    ActionExtraction,
    Condition,
    EntityExtraction,
    ParseResult,
    RawParameter,
    TemporalCue,
)
from src.pipeline.analyzer import analyze, AnalysisResult


@pytest.fixture
def registry():
    return create_registry()


def make_parse_result(
    actions=None, entities=None, temporal_cues=None, conditions=None, raw_parameters=None
):
    return ParseResult(
        actions=actions or [],
        entities=entities or [],
        temporal_cues=temporal_cues or [],
        conditions=conditions or [],
        raw_parameters=raw_parameters or [],
    )


class TestActionResolution:
    def test_resolves_known_action_by_verb_and_object(self, registry):
        pr = make_parse_result(actions=[
            ActionExtraction(verb="pull", object="data", original_text="pull data from CRM"),
        ])
        result = analyze(pr, registry=registry)
        assert len(result.resolved_actions) == 1
        assert result.resolved_actions[0].catalog_action is not None
        assert result.resolved_actions[0].catalog_action.action_id == "fetch_data"

    def test_resolves_email_action(self, registry):
        pr = make_parse_result(actions=[
            ActionExtraction(verb="email", object="report", original_text="email the report to the team"),
        ])
        result = analyze(pr, registry=registry)
        assert result.resolved_actions[0].catalog_action is not None
        assert result.resolved_actions[0].catalog_action.action_id == "send_email"

    def test_resolves_summarize_to_transform(self, registry):
        pr = make_parse_result(actions=[
            ActionExtraction(verb="summarize", object="data", original_text="summarize it"),
        ])
        result = analyze(pr, registry=registry)
        assert result.resolved_actions[0].catalog_action is not None
        assert result.resolved_actions[0].catalog_action.action_id == "transform_data"

    def test_unresolvable_action_flagged_as_ambiguity(self, registry):
        pr = make_parse_result(actions=[
            ActionExtraction(verb="dance", object="jig", original_text="dance a jig"),
        ])
        result = analyze(pr, registry=registry)
        assert len(result.ambiguities) == 1
        assert "dance" in result.ambiguities[0].options[0].lower()

    def test_unresolvable_in_non_strict_creates_assumption(self, registry):
        pr = make_parse_result(actions=[
            ActionExtraction(verb="dance", object="jig", original_text="dance a jig"),
        ])
        result = analyze(pr, registry=registry, strict_mode=False)
        assert any("generic action" in a for a in result.assumptions)

    def test_unresolvable_in_strict_still_flags_ambiguity(self, registry):
        pr = make_parse_result(actions=[
            ActionExtraction(verb="dance", object="jig", original_text="dance a jig"),
        ])
        result = analyze(pr, registry=registry, strict_mode=True)
        assert len(result.ambiguities) == 1


class TestOrdering:
    def test_sequential_ordering(self, registry):
        pr = make_parse_result(actions=[
            ActionExtraction(verb="pull", object="data", original_text="pull data"),
            ActionExtraction(verb="summarize", object="data", original_text="summarize it"),
            ActionExtraction(verb="email", object="report", original_text="email the report"),
        ])
        result = analyze(pr, registry=registry)
        assert result.ordering == ["step_1", "step_2", "step_3"]

    def test_sequential_assumption_recorded(self, registry):
        pr = make_parse_result(actions=[
            ActionExtraction(verb="pull", object="data", original_text="pull data"),
            ActionExtraction(verb="email", object="report", original_text="email it"),
        ])
        result = analyze(pr, registry=registry)
        assert any("sequentially" in a for a in result.assumptions)


class TestEntityCrossReferencing:
    def test_later_step_gets_input_from_earlier(self, registry):
        pr = make_parse_result(
            actions=[
                ActionExtraction(verb="pull", object="sales data", original_text="pull sales data"),
                ActionExtraction(verb="summarize", object="sales data", original_text="summarize it"),
            ],
            entities=[
                EntityExtraction(name="sales data", type="data", context="data to pull"),
            ],
        )
        result = analyze(pr, registry=registry)
        step_2 = result.resolved_actions[1]
        assert any("step_1" in v for v in step_2.inputs.values())


class TestTemporalAndConditions:
    def test_temporal_cues_carried_forward(self, registry):
        pr = make_parse_result(
            actions=[ActionExtraction(verb="pull", object="data", original_text="pull data")],
            temporal_cues=[TemporalCue(text="every Monday", type="schedule", cron="0 9 * * 1")],
        )
        result = analyze(pr, registry=registry)
        assert len(result.temporal_cues) == 1
        assert result.temporal_cues[0]["cron"] == "0 9 * * 1"

    def test_conditions_carried_forward(self, registry):
        pr = make_parse_result(
            actions=[ActionExtraction(verb="notify", object="oncall", original_text="notify oncall")],
            conditions=[Condition(text="if CPU > 90%", type="if", expression="cpu_usage > 90")],
        )
        result = analyze(pr, registry=registry)
        assert len(result.conditions) == 1
        assert result.conditions[0]["expression"] == "cpu_usage > 90"

    def test_parameters_carried_forward(self, registry):
        pr = make_parse_result(
            actions=[ActionExtraction(verb="pull", object="data", original_text="pull data")],
            raw_parameters=[RawParameter(name="source", value="{source}", type="string")],
        )
        result = analyze(pr, registry=registry)
        assert len(result.raw_parameters) == 1
        assert result.raw_parameters[0]["name"] == "source"
