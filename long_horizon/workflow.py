from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import read_toml, write_toml


DEFAULT_FLOW: dict[str, Any] = {
    "flow": {"id": "default", "initial_state": "understand", "terminal_states": ["completed", "cancelled"]},
    "states": [
        {"id": "understand", "kind": "work"},
        {"id": "implement", "kind": "work"},
        {"id": "review", "kind": "gate"},
        {"id": "completed", "kind": "terminal"},
    ],
    "transitions": [
        {"from": "understand", "to": "implement", "requires_artifacts": ["artifacts/plan.md"]},
        {"from": "implement", "to": "review", "requires_checks": ["tests_passed"]},
        {"from": "review", "to": "completed", "requires_human": False},
    ],
}


def write_default_flow(path: Path) -> None:
    write_toml(path, DEFAULT_FLOW)


def load_flow(path: Path) -> dict[str, Any]:
    return read_toml(path)


def state_ids(flow: dict[str, Any]) -> set[str]:
    return {state["id"] for state in flow.get("states", [])}


def allowed_next(flow: dict[str, Any], current: str) -> list[str]:
    return [t["to"] for t in flow.get("transitions", []) if t.get("from") == current]


def find_transition(flow: dict[str, Any], current: str, to_state: str) -> dict[str, Any] | None:
    for transition in flow.get("transitions", []):
        if transition.get("from") == current and transition.get("to") == to_state:
            return transition
    return None
