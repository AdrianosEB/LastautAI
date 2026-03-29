from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Action:
    action_id: str
    aliases: list[str]
    required_inputs: list[dict]
    outputs: list[dict]
    service: str = ""


@dataclass
class ActionRegistry:
    _actions: dict[str, Action] = field(default_factory=dict)
    _alias_index: dict[str, str] = field(default_factory=dict)

    def load_directory(self, directory: str | Path) -> None:
        directory = Path(directory)
        for yaml_file in sorted(directory.glob("*.yaml")):
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
            action = Action(
                action_id=data["action_id"],
                aliases=data.get("aliases", []),
                required_inputs=data.get("required_inputs", []),
                outputs=data.get("outputs", []),
                service=data.get("service", ""),
            )
            self._actions[action.action_id] = action
            for alias in action.aliases:
                self._alias_index[alias.lower()] = action.action_id

    def lookup(self, phrase: str) -> Action | None:
        normalized = phrase.lower().strip()
        if not normalized:
            return None

        if normalized in self._alias_index:
            return self._actions[self._alias_index[normalized]]

        for alias, action_id in self._alias_index.items():
            if alias in normalized or normalized in alias:
                return self._actions[action_id]

        return None

    def get(self, action_id: str) -> Action | None:
        return self._actions.get(action_id)

    def all_actions(self) -> list[Action]:
        return list(self._actions.values())


def create_registry() -> ActionRegistry:
    registry = ActionRegistry()
    actions_dir = Path(__file__).parent / "actions"
    if actions_dir.exists():
        registry.load_directory(actions_dir)
    return registry
