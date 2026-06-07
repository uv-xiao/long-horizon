from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import read_toml, write_toml
from .paths import lh_root


DEFAULT_CONFIG: dict[str, Any] = {
    "agent": {"substrate": "codex-goal", "goal_mode": True, "process_adapter": "brief"},
    "process": {
        "workspace_mode": "worktree",
        "state_model": "copy_on_write",
        "recovery": "resumable",
        "branch_policy": "code_changes_require_branch",
    },
    "git": {"commit_policy": "meaningful_units"},
    "workflow": {"transition_policy": "python_validators", "waits": "flow_declared"},
    "logging": {"mode": "typed_plus_loose", "hash_chain": True},
    "observer": {"modes": ["checkpoint", "sidecar"], "workspace_policy": "attach"},
    "report": {"formats": ["html", "markdown"], "timeline_analysis": False, "serve": "optional"},
    "comments": {"ingestion": "push_inbox_primary"},
}

ALLOWED = {
    ("agent", "substrate"): {"codex-goal", "codex", "manual", "claude-code", "humanize", "native-process-agent"},
    ("process", "workspace_mode"): {"worktree", "original_checkout", "branchless_read_only", "native_process"},
    ("process", "branch_policy"): {"code_changes_require_branch", "read_only_branchless"},
    ("logging", "mode"): {"typed_plus_loose", "strict_typed", "loose"},
    ("workflow", "waits"): {"flow_declared"},
}


def config_path(root: str | Path) -> Path:
    return lh_root(root) / "config.toml"


def load_config(root: str | Path) -> dict[str, Any]:
    path = config_path(root)
    if not path.exists():
        return DEFAULT_CONFIG
    return read_toml(path)


def write_default_config(root: str | Path) -> None:
    write_toml(config_path(root), DEFAULT_CONFIG)


def validate_config_data(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for section in DEFAULT_CONFIG:
        if section not in data or not isinstance(data[section], dict):
            errors.append(f"missing section {section}")
    for (section, key), allowed in ALLOWED.items():
        value = data.get(section, {}).get(key)
        if value not in allowed:
            errors.append(f"invalid {section}.{key}: {value!r}")
    if data.get("process", {}).get("workspace_mode") == "branchless_read_only":
        if data.get("process", {}).get("branch_policy") != "read_only_branchless":
            errors.append("branchless_read_only requires read_only_branchless branch policy")
    return errors


def validate_config(root: str | Path) -> list[str]:
    return validate_config_data(load_config(root))


def set_config_value(root: str | Path, dotted_key: str, value: str) -> dict[str, Any]:
    data = load_config(root)
    section, key = dotted_key.split(".", 1)
    if section not in data or not isinstance(data[section], dict):
        data[section] = {}
    data[section][key] = _coerce(value)
    errors = validate_config_data(data)
    if errors:
        raise ValueError("; ".join(errors))
    write_toml(config_path(root), data)
    return data


def _coerce(value: str) -> Any:
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if "," in value:
        return [part.strip() for part in value.split(",") if part.strip()]
    return value
