from __future__ import annotations

from pathlib import Path

from .config import write_default_config
from .io import copy_file, ensure_dir, read_text, write_text
from .paths import lh_root
from .time import now_iso
from .workflow import write_default_flow


AGENTS_BLOCK = """

## Long-Horizon Runtime

This repository uses the long-horizon template. Agent-facing rules and skills
live under `.agents/`; runtime state, goals, logs, artifacts, inboxes, and
reports live under `.long-horizon/`.

Agents should read `.agents/rules/long-horizon.md` and use the installed
long-horizon skills before operating on `.long-horizon/` state.
"""


def install(target: str | Path, apply: bool = False) -> Path:
    root = Path(target).resolve()
    plan = _install_plan(root)
    plan_path = lh_root(root) / "install-plan.md"
    ensure_dir(plan_path.parent)
    write_text(plan_path, plan)
    if not apply:
        return plan_path
    _apply(root)
    return plan_path


def _install_plan(root: Path) -> str:
    existing = [name for name in ["AGENTS.md", "CLAUDE.md", ".agents", ".claude", ".github", ".gitignore"] if (root / name).exists()]
    return "\n".join(
        [
            "# Long-Horizon Install Plan",
            "",
            f"Target: {root}",
            f"Created at: {now_iso()}",
            "",
            "## Existing Agent Surfaces",
            *(f"- {item}" for item in existing),
            "",
            "## Proposed Changes",
            "- Add or extend `AGENTS.md` with a long-horizon entrypoint.",
            "- Install agent-facing rules and skills under `.agents/`.",
            "- Install runtime state under `.long-horizon/`.",
            "- Add `.long-horizon/` to `.gitignore`.",
            "",
        ]
    )


def _apply(root: Path) -> None:
    ensure_dir(root / ".agents" / "rules")
    ensure_dir(root / ".agents" / "skills")
    ensure_dir(root / ".agents" / "lib" / "long-horizon")
    ensure_dir(root / ".agents" / "lib" / "github")
    ensure_dir(lh_root(root) / "flows")
    for d in ["inbox/comments", "goals", "logs", "artifacts", "reports", "memory"]:
        ensure_dir(lh_root(root) / d)
    write_default_config(root)
    _copy_catalog(root)
    write_default_flow(lh_root(root) / "flows" / "default.toml")
    write_text(lh_root(root) / "agent-capabilities.md", "# Agent Capabilities\n\n- substrate: codex-goal\n- process adapter: generated brief\n")
    write_text(root / ".agents" / "rules" / "long-horizon.md", _long_horizon_rule())
    write_text(root / ".agents" / "rules" / "github-cli.md", _github_rule())
    for skill in [
        "configure-long-horizon",
        "update-long-horizon-policy",
        "start-long-horizon-task",
        "resume-long-horizon-process",
        "inspect-long-horizon-report",
        "address-long-horizon-comment",
    ]:
        write_text(root / ".agents" / "skills" / skill / "SKILL.md", _skill(skill))
    _merge_agents(root)
    _merge_gitignore(root)
    from .io import append_jsonl

    append_jsonl(lh_root(root) / "logs" / "install.jsonl", {"created_at": now_iso(), "event": "install_applied"})


def _copy_catalog(root: Path) -> None:
    src = Path(__file__).resolve().parent.parent / "templates" / ".long-horizon" / "config-catalog.md"
    if src.exists():
        copy_file(src, lh_root(root) / "config-catalog.md")
    else:
        write_text(lh_root(root) / "config-catalog.md", "# Long-Horizon Configuration Catalog\n")


def _merge_agents(root: Path) -> None:
    path = root / "AGENTS.md"
    existing = read_text(path)
    if "## Long-Horizon Runtime" not in existing:
        write_text(path, (existing.rstrip() + AGENTS_BLOCK + "\n").lstrip())


def _merge_gitignore(root: Path) -> None:
    path = root / ".gitignore"
    existing = read_text(path)
    if ".long-horizon/" not in existing:
        write_text(path, existing.rstrip() + "\n.long-horizon/\n")


def _long_horizon_rule() -> str:
    return "# Long-Horizon Rule\n\nUse `.agents/` for operating instructions and `.long-horizon/` for runtime state. Workflow boards advance only through the transition command. Canonical ledgers are append-only and should be written through the logger.\n"


def _github_rule() -> str:
    return "# GitHub CLI Rule\n\nUse repository-local GitHub CLI configuration when configured. If auth is unavailable, stop and ask the human to configure it instead of silently using unrelated global credentials.\n"


def _skill(name: str) -> str:
    title = name.replace("-", " ").title()
    return f"---\nname: {name}\ndescription: Operate the long-horizon runtime task surface for {title.lower()}.\n---\n\n# {title}\n\nRead `.agents/rules/long-horizon.md`, inspect `.long-horizon/config.toml`, and use `python -m long_horizon` commands for canonical state changes.\n"
