from __future__ import annotations

from pathlib import Path
import copy
from typing import Any

from .io import read_toml, write_toml
from .paths import lh_root


DEFAULT_CONFIG: dict[str, Any] = {
    "features": {
        "runtime_state": True,
        "prompt_templates": True,
        "transition_validation": True,
        "message_mailboxes": True,
        "local_supervisor": False,
        "native_agent_loop": False,
        "report_server": True,
        "github_channel": False,
    },
    "profile": {"label": "mixed", "derived_from": "features"},
    "agent": {"substrate": "codex-goal", "goal_mode": True, "process_adapter": "brief", "operation_mode": "hybrid"},
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
    "supervisor": {"enabled": False, "restart_policy": "never"},
    "notifications": {"channels": ["local", "github"], "default_channel": "local"},
    "retention": {"policy": "compress_copy", "min_bytes": 1048576},
    "ledger_recovery": {"mode": "preserve_and_reconcile"},
    "report_gui": {"adapter_boundary": "report-data-json"},
    "evaluation": {"adapters": ["command", "file_contains", "metric_threshold"]},
}

ALLOWED = {
    ("agent", "substrate"): {"codex-goal", "codex", "manual", "claude-code", "humanize", "native-process-agent"},
    ("agent", "operation_mode"): {"runtime-owned", "native-agent", "hybrid"},
    ("process", "workspace_mode"): {"worktree", "original_checkout", "branchless_read_only", "native_process"},
    ("process", "branch_policy"): {"code_changes_require_branch", "read_only_branchless"},
    ("logging", "mode"): {"typed_plus_loose", "strict_typed", "loose"},
    ("workflow", "waits"): {"flow_declared"},
    ("profile", "label"): {"runtime-heavy", "native-agent-heavy", "mixed", "prompt-only"},
    ("supervisor", "restart_policy"): {"never", "on_failure"},
    ("notifications", "default_channel"): {"local", "github"},
    ("retention", "policy"): {"compress_copy", "archive_copy", "externalize_ref"},
    ("ledger_recovery", "mode"): {"preserve_and_reconcile"},
    ("report_gui", "adapter_boundary"): {"report-data-json"},
}

FEATURE_KEYS = set(DEFAULT_CONFIG["features"])


def config_path(root: str | Path) -> Path:
    return lh_root(root) / "config.toml"


def load_config(root: str | Path) -> dict[str, Any]:
    path = config_path(root)
    if not path.exists():
        return copy.deepcopy(DEFAULT_CONFIG)
    return normalize_config(read_toml(path))


def write_default_config(root: str | Path, operation_mode: str | None = None) -> None:
    data = copy.deepcopy(DEFAULT_CONFIG)
    if operation_mode:
        data.setdefault("agent", {})["operation_mode"] = operation_mode
    data = normalize_config(data)
    write_toml(config_path(root), data)


def validate_config_data(data: dict[str, Any]) -> list[str]:
    data = normalize_config(data)
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
    features = data.get("features", {})
    for key in FEATURE_KEYS:
        if key not in features:
            errors.append(f"missing features.{key}")
        elif not isinstance(features[key], bool):
            errors.append(f"features.{key} must be boolean")
    if features.get("runtime_state"):
        if not features.get("transition_validation"):
            errors.append("features.runtime_state requires features.transition_validation")
        if not features.get("message_mailboxes"):
            errors.append("features.runtime_state requires features.message_mailboxes")
    return errors


def validate_config(root: str | Path) -> list[str]:
    return validate_config_data(load_config(root))


def set_config_value(root: str | Path, dotted_key: str, value: str) -> dict[str, Any]:
    data = load_config(root)
    section, key = dotted_key.split(".", 1)
    if section not in data or not isinstance(data[section], dict):
        data[section] = {}
    data[section][key] = _coerce(value)
    data = normalize_config(data)
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


def normalize_config(data: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(DEFAULT_CONFIG)
    for section, values in data.items():
        if isinstance(values, dict) and isinstance(normalized.get(section), dict):
            normalized[section].update(values)
        else:
            normalized[section] = values
    features = normalized.setdefault("features", {})
    mode = str(normalized.get("agent", {}).get("operation_mode", "hybrid"))
    if "features" not in data or not isinstance(data.get("features"), dict):
        features.update(features_from_operation_mode(mode))
    if features.get("runtime_state"):
        features["transition_validation"] = True
        features["message_mailboxes"] = True
    normalized["profile"] = {
        "label": derive_profile_label(features),
        "derived_from": "features",
    }
    normalized["responsibility"] = responsibility_map(features, mode)
    return normalized


def features_from_operation_mode(operation_mode: str) -> dict[str, bool]:
    if operation_mode == "native-agent":
        return {
            "runtime_state": True,
            "prompt_templates": True,
            "transition_validation": True,
            "message_mailboxes": True,
            "local_supervisor": False,
            "native_agent_loop": True,
            "report_server": True,
            "github_channel": False,
        }
    if operation_mode == "runtime-owned":
        return {
            "runtime_state": True,
            "prompt_templates": True,
            "transition_validation": True,
            "message_mailboxes": True,
            "local_supervisor": False,
            "native_agent_loop": False,
            "report_server": True,
            "github_channel": False,
        }
    return copy.deepcopy(DEFAULT_CONFIG["features"])


def derive_profile_label(features: dict[str, Any]) -> str:
    if not features.get("runtime_state") and features.get("prompt_templates"):
        return "prompt-only"
    if features.get("native_agent_loop") and features.get("runtime_state"):
        return "native-agent-heavy"
    if features.get("runtime_state") and not features.get("native_agent_loop"):
        return "runtime-heavy"
    return "mixed"


def responsibility_map(features: dict[str, Any], operation_mode: str = "hybrid") -> dict[str, list[str] | str]:
    template: list[str] = []
    agent: list[str] = []
    if features.get("runtime_state"):
        template.extend(["goal/run state", "process metadata", "workflow evidence"])
    if features.get("transition_validation"):
        template.append("transition validation")
    if features.get("message_mailboxes"):
        template.append("process mailboxes")
    if features.get("report_server"):
        template.append("human report data")
    if features.get("prompt_templates"):
        template.append("phase prompts and skills")
    if features.get("native_agent_loop"):
        agent.append("native continuation loop")
    else:
        agent.append("execute generated briefs")
    return {
        "source": "features",
        "legacy_operation_mode": operation_mode,
        "template": template,
        "target_agent": agent,
    }
