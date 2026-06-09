from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .config import derive_profile_label, features_from_operation_mode, responsibility_map
from .io import read_text, read_toml, write_text, write_toml
from .paths import lh_root
from .time import now_iso


OPERATION_MODES = {"runtime-owned", "native-agent", "hybrid"}

ROOT_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    ".mcp.json",
    "hooks.json",
    ".gitignore",
    "pyproject.toml",
    "package.json",
]
ROOT_DIRS = [
    ".agents",
    ".claude",
    ".cursor",
    ".humanize",
    ".github/workflows",
    "commands",
    "agents",
    "hooks",
    "scripts",
]
TEXT_SUFFIXES = {".md", ".toml", ".json", ".yaml", ".yml", ".txt", ".sh"}
LONG_HORIZON_SKILLS = {
    "analyze-target-agent",
    "install-long-horizon",
    "start-long-horizon-task",
    "create-goal-contract",
    "assemble-goal-flow",
    "start-execution",
    "operate-long-horizon-process",
    "complete-and-deposit",
    "configure-long-horizon",
    "update-long-horizon-policy",
}


def capabilities_path(root: str | Path) -> Path:
    return lh_root(root) / "agent-capabilities.toml"


def analyze_target(
    root: str | Path,
    target_agent: str = "auto",
    operation_mode: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    repo = Path(root).resolve()
    fingerprint, inputs = _fingerprint(repo, target_agent)
    cache = capabilities_path(repo)
    if not force and cache.exists():
        cached = read_toml(cache)
        if cached.get("analysis", {}).get("fingerprint") == fingerprint:
            cached.setdefault("analysis", {})["cache_status"] = "reused"
            write_toml(cache, cached)
            write_capability_markdown(repo, cached)
            write_operation_mode_decision(repo, cached)
            return cached
    detected = _detect(repo)
    mode = _choose_mode(target_agent, detected, operation_mode)
    feature_settings = features_from_operation_mode(mode)
    data = {
        "analysis": {
            "created_at": now_iso(),
            "cache_status": "refreshed",
            "fingerprint": fingerprint,
            "target_agent": target_agent,
            "operation_mode": mode,
            "profile_label": derive_profile_label(feature_settings),
            "input_paths": inputs,
        },
        "features": detected,
        "feature_settings": feature_settings,
        "responsibility": responsibility_map(feature_settings, mode),
        "mode": _mode_details(mode, target_agent, detected),
    }
    write_toml(cache, data)
    write_capability_markdown(repo, data)
    write_operation_mode_decision(repo, data)
    return data


def load_capabilities(root: str | Path) -> dict[str, Any]:
    path = capabilities_path(root)
    if not path.exists():
        return analyze_target(root)
    return read_toml(path)


def selected_operation_mode(root: str | Path) -> str:
    data = load_capabilities(root)
    return str(data.get("analysis", {}).get("operation_mode", "runtime-owned"))


def write_capability_markdown(root: str | Path, data: dict[str, Any]) -> Path:
    path = lh_root(root) / "agent-capabilities.md"
    analysis = data.get("analysis", {})
    features = data.get("features", {})
    mode = data.get("mode", {})
    feature_settings = data.get("feature_settings", {})
    responsibility = data.get("responsibility", {})
    lines = [
        "# Agent Capability Analysis",
        "",
        f"Created at: {analysis.get('created_at', '')}",
        f"Cache status: `{analysis.get('cache_status', '')}`",
        f"Target agent: `{analysis.get('target_agent', '')}`",
        f"Selected operation mode: `{analysis.get('operation_mode', '')}`",
        f"Derived feature profile: `{analysis.get('profile_label', '')}`",
        "",
        "## Feature Settings",
    ]
    for key in sorted(feature_settings):
        lines.append(f"- `{key}`: `{feature_settings[key]}`")
    lines.extend(
        [
            "",
            "## Responsibility Map",
            "",
            "Template owns:",
        ]
    )
    for item in responsibility.get("template", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Target agent owns:")
    for item in responsibility.get("target_agent", []):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Detected Features",
        ]
    )
    for key in sorted(features):
        lines.append(f"- `{key}`: `{features[key]}`")
    lines.extend(
        [
            "",
            "## Mode Decision",
            "",
            str(mode.get("rationale", "")),
            "",
            "## Template Responsibilities",
        ]
    )
    for item in mode.get("template_responsibilities", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Native-Agent Responsibilities")
    for item in mode.get("native_agent_responsibilities", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Inputs")
    for item in analysis.get("input_paths", []):
        lines.append(f"- `{item}`")
    write_text(path, "\n".join(lines).rstrip() + "\n")
    return path


def write_operation_mode_decision(root: str | Path, data: dict[str, Any]) -> Path:
    path = lh_root(root) / "decisions" / "operation-mode.md"
    analysis = data.get("analysis", {})
    mode = data.get("mode", {})
    feature_settings = data.get("feature_settings", {})
    lines = [
        "# Feature Settings Decision",
        "",
        f"Derived profile: `{analysis.get('profile_label', '')}`",
        f"Compatibility operation mode: `{analysis.get('operation_mode', '')}`",
        f"Target agent: `{analysis.get('target_agent', '')}`",
        f"Fingerprint: `{analysis.get('fingerprint', '')}`",
        "",
        "## Feature Settings",
        "",
        *(f"- `{key}`: `{feature_settings[key]}`" for key in sorted(feature_settings)),
        "",
        "## Rationale",
        "",
        str(mode.get("rationale", "")),
        "",
        "## Alternatives",
        "",
        "- `runtime-owned`: template owns durable runtime and process mechanics.",
        "- `native-agent`: target agent owns loop/process orchestration; template supplies prompts, policy, evidence, and validators.",
        "- `hybrid`: target agent owns part of orchestration while template owns durable workflow state, reporting, or workspace/version control.",
        "",
        "## Override",
        "",
        "Edit `[features]` in `.long-horizon/config.toml` or rerun install/task intake with an explicit compatibility override. Runtime state always enables transition validation and process mailboxes.",
    ]
    write_text(path, "\n".join(lines).rstrip() + "\n")
    return path


def _fingerprint(root: Path, target_agent: str) -> tuple[str, list[str]]:
    digest = hashlib.sha256()
    digest.update(f"target_agent={target_agent}\n".encode("utf-8"))
    paths = _analysis_inputs(root)
    rels: list[str] = []
    for path in paths:
        rel = path.relative_to(root).as_posix()
        rels.append(rel)
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        if path.is_file():
            digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest(), rels


def _analysis_inputs(root: Path) -> list[Path]:
    paths: list[Path] = []
    for rel in ROOT_FILES:
        path = root / rel
        if path.exists():
            paths.append(path)
    for rel in ROOT_DIRS:
        base = root / rel
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix in TEXT_SUFFIXES and not _is_installed_long_horizon_asset(root, path):
                paths.append(path)
    return sorted(set(paths))


def _is_installed_long_horizon_asset(root: Path, path: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    if rel.startswith(".agents/templates/long-horizon/"):
        return True
    if rel == ".agents/rules/long-horizon.md":
        return True
    parts = rel.split("/")
    if len(parts) >= 4 and parts[0] == ".agents" and parts[1] == "skills" and parts[2] in LONG_HORIZON_SKILLS:
        return True
    return False


def _detect(root: Path) -> dict[str, Any]:
    texts = []
    for path in _analysis_inputs(root):
        texts.append(read_text(path).lower())
    merged = "\n".join(texts)
    has_agents = (root / ".agents").exists() or (root / "AGENTS.md").exists()
    has_claude = (root / ".claude").exists() or (root / "CLAUDE.md").exists()
    has_humanize = (root / ".humanize").exists() or "humanize" in merged or "rlcr" in merged
    hooks = (root / "hooks.json").exists() or (root / ".claude" / "hooks.json").exists() or "stop hook" in merged or "hooks" in merged
    subagents = (root / "agents").exists() or "subagent" in merged or "task tool" in merged
    review = "codex review" in merged or "review" in merged or "pr review" in merged
    process_management = "tmux" in merged or "process" in merged or "session" in merged or "worktree" in merged
    native_loop = has_humanize or "goal tracker" in merged or "rlcr" in merged or "loop" in merged
    return {
        "agent_rules": has_agents,
        "claude_surface": has_claude,
        "humanize_surface": has_humanize,
        "native_hooks": hooks,
        "native_subagents": subagents,
        "native_review": review,
        "native_process_management": process_management,
        "native_long_loop": native_loop,
        "github_surface": (root / ".github").exists() or "github" in merged,
    }


def _choose_mode(target_agent: str, features: dict[str, Any], override: str | None) -> str:
    if override:
        if override not in OPERATION_MODES:
            raise ValueError(f"invalid operation mode {override!r}")
        return override
    target = target_agent.lower()
    if target in {"codex-goal", "codex-/goal"}:
        return "hybrid"
    if target in {"manual", "codex"}:
        return "runtime-owned"
    strong_native = (
        bool(features.get("native_long_loop"))
        and bool(features.get("native_hooks") or features.get("native_subagents"))
        and bool(features.get("native_review") or features.get("native_process_management"))
    )
    if target in {"humanize", "claude-code", "native-process-agent"} and strong_native:
        return "native-agent"
    if strong_native and target == "auto":
        return "native-agent"
    if features.get("native_long_loop") or features.get("native_hooks") or features.get("native_subagents"):
        return "hybrid"
    return "runtime-owned"


def _mode_details(mode: str, target_agent: str, features: dict[str, Any]) -> dict[str, Any]:
    if mode == "runtime-owned":
        return {
            "rationale": "The target agent does not expose enough native long-loop orchestration, so the template installs the full runtime surface and prompt-guided commands.",
            "template_responsibilities": [
                "own `.long-horizon/` workflow state, ledgers, reports, comments, and recovery briefs",
                "provide phase prompts plus Python validation/transition/report commands",
                "guide process restart and fork/join through template state",
            ],
            "native_agent_responsibilities": ["execute the generated briefs and write requested artifacts"],
        }
    if mode == "native-agent":
        return {
            "rationale": "The target agent already has native loop/orchestration features; the template should configure and audit those features instead of duplicating the loop.",
            "template_responsibilities": [
                "provide goal-contract, flow, evidence, and review prompts",
                "supply validators, policy overlays, and report/comment artifacts when useful",
                "record capability and operation-mode decisions for audit",
            ],
            "native_agent_responsibilities": [
                "own loop execution, stop hooks, subagents, review, or process/session controls",
                "call template validators or write evidence artifacts at declared gates",
            ],
        }
    return {
        "rationale": f"The selected target agent `{target_agent}` has partial orchestration or persistent-session capability, while the template still needs durable workflow state, evidence gates, reporting, or workspace control.",
        "template_responsibilities": [
            "own durable contracts, flow snapshots, transition validation, reports, and evidence ledgers",
            "provide phase prompts and runtime commands where native features are incomplete",
        ],
        "native_agent_responsibilities": [
            "own available native continuation, hooks, subagents, or review features",
            "consume generated briefs without letting the template compete with the native loop",
        ],
    }
