import pytest
from pathlib import Path

from src.catalog.registry import ActionRegistry, create_registry


@pytest.fixture
def registry():
    return create_registry()


class TestCatalogLoading:
    def test_loads_all_actions(self, registry):
        actions = registry.all_actions()
        assert len(actions) == 6

    def test_all_action_ids_present(self, registry):
        expected = {
            "fetch_data", "transform_data", "send_email",
            "send_notification", "write_file", "http_request",
        }
        actual = {a.action_id for a in registry.all_actions()}
        assert actual == expected

    def test_action_has_aliases(self, registry):
        action = registry.get("fetch_data")
        assert action is not None
        assert len(action.aliases) > 0

    def test_action_has_required_inputs(self, registry):
        action = registry.get("send_email")
        assert action is not None
        assert len(action.required_inputs) > 0
        input_names = [i["name"] for i in action.required_inputs]
        assert "to" in input_names

    def test_action_has_outputs(self, registry):
        action = registry.get("http_request")
        assert action is not None
        assert len(action.outputs) > 0


class TestCatalogLookup:
    def test_exact_alias_match(self, registry):
        action = registry.lookup("fetch data")
        assert action is not None
        assert action.action_id == "fetch_data"

    def test_exact_alias_case_insensitive(self, registry):
        action = registry.lookup("Send Email")
        assert action is not None
        assert action.action_id == "send_email"

    def test_substring_match(self, registry):
        action = registry.lookup("pull data from the CRM")
        assert action is not None
        assert action.action_id == "fetch_data"

    def test_alias_contained_in_phrase(self, registry):
        action = registry.lookup("please notify the team")
        assert action is not None
        assert action.action_id == "send_notification"

    def test_lookup_miss(self, registry):
        action = registry.lookup("dance a jig")
        assert action is None

    def test_lookup_empty_string(self, registry):
        action = registry.lookup("")
        assert action is None


class TestRegistryGet:
    def test_get_existing(self, registry):
        action = registry.get("write_file")
        assert action is not None
        assert action.action_id == "write_file"

    def test_get_missing(self, registry):
        assert registry.get("nonexistent") is None
