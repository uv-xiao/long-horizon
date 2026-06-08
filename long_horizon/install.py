from __future__ import annotations

from pathlib import Path

from .capabilities import analyze_target
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


def install(
    target: str | Path,
    apply: bool = False,
    target_agent: str = "auto",
    operation_mode: str | None = None,
    force_analyze: bool = False,
) -> Path:
    root = Path(target).resolve()
    capabilities = analyze_target(root, target_agent=target_agent, operation_mode=operation_mode, force=force_analyze)
    plan = _install_plan(root, capabilities)
    plan_path = lh_root(root) / "install-plan.md"
    ensure_dir(plan_path.parent)
    write_text(plan_path, plan)
    if not apply:
        return plan_path
    _apply(root, capabilities)
    return plan_path


def _install_plan(root: Path, capabilities: dict) -> str:
    existing = [name for name in ["AGENTS.md", "CLAUDE.md", ".agents", ".claude", ".github", ".gitignore"] if (root / name).exists()]
    mode = capabilities.get("analysis", {}).get("operation_mode", "runtime-owned")
    details = capabilities.get("mode", {})
    return "\n".join(
        [
            "# Long-Horizon Install Plan",
            "",
            f"Target: {root}",
            f"Created at: {now_iso()}",
            f"Operation mode: `{mode}`",
            "",
            "## Existing Agent Surfaces",
            *(f"- {item}" for item in existing),
            "",
            "## Capability Decision",
            str(details.get("rationale", "")),
            "",
            "## Proposed Changes",
            "- Add or extend `AGENTS.md` with a long-horizon entrypoint.",
            "- Install prompt-first long-horizon skills under `.agents/skills/`.",
            "- Install phase prompt templates under `.agents/templates/long-horizon/`.",
            "- Install runtime/config/evidence state under `.long-horizon/` as required by the selected mode.",
            "- Add `.long-horizon/` to `.gitignore`.",
            "",
            "## Native-Agent Feature Handling",
            *(
                f"- {item}"
                for item in details.get(
                    "native_agent_responsibilities",
                    ["No native-agent responsibilities detected; template runtime owns the loop."],
                )
            ),
            "",
            "## Template Responsibilities",
            *(f"- {item}" for item in details.get("template_responsibilities", [])),
            "",
        ]
    )


def _apply(root: Path, capabilities: dict) -> None:
    ensure_dir(root / ".agents" / "rules")
    ensure_dir(root / ".agents" / "skills")
    ensure_dir(root / ".agents" / "templates" / "long-horizon")
    ensure_dir(root / ".agents" / "lib" / "long-horizon")
    ensure_dir(root / ".agents" / "lib" / "github")
    ensure_dir(lh_root(root) / "flows")
    ensure_dir(lh_root(root) / "decisions")
    for d in ["inbox/comments", "goals", "logs", "artifacts", "reports", "memory"]:
        ensure_dir(lh_root(root) / d)
    mode = str(capabilities.get("analysis", {}).get("operation_mode", "runtime-owned"))
    write_default_config(root, operation_mode=mode)
    _copy_catalog(root)
    write_default_flow(lh_root(root) / "flows" / "default.toml")
    write_text(root / ".agents" / "rules" / "long-horizon.md", _long_horizon_rule())
    write_text(root / ".agents" / "rules" / "github-cli.md", _github_rule())
    _copy_template_tree(root)
    _merge_agents(root)
    _merge_gitignore(root)
    from .io import append_jsonl

    append_jsonl(lh_root(root) / "logs" / "install.jsonl", {"created_at": now_iso(), "event": "install_applied", "operation_mode": mode})


def _copy_catalog(root: Path) -> None:
    src = Path(__file__).resolve().parent.parent / "templates" / ".long-horizon" / "config-catalog.md"
    if src.exists():
        copy_file(src, lh_root(root) / "config-catalog.md")
    else:
        write_text(lh_root(root) / "config-catalog.md", "# Long-Horizon Configuration Catalog\n")


def _copy_template_tree(root: Path) -> None:
    src_root = Path(__file__).resolve().parent.parent / "templates"
    skills_src = src_root / ".agents" / "skills"
    if skills_src.exists():
        for skill_file in skills_src.glob("*/SKILL.md"):
            copy_file(skill_file, root / ".agents" / "skills" / skill_file.parent.name / "SKILL.md")
    prompts_src = src_root / "prompts"
    prompts_dst = root / ".agents" / "templates" / "long-horizon"
    if prompts_src.exists():
        for prompt in prompts_src.glob("*.md"):
            copy_file(prompt, prompts_dst / prompt.name)


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
    return "# Long-Horizon Rule\n\nUse `.agents/` for operating instructions and `.long-horizon/` for runtime state. Start with `analyze-target-agent`, then use the phase skills in order: install, task setup, goal contract, flow assembly, execution start, live operation, completion, and deposition. Workflow boards advance only through the transition command when the selected operation mode uses template-owned runtime state. Canonical ledgers are append-only and should be written through the logger.\n"


def _github_rule() -> str:
    return "# GitHub CLI Rule\n\nUse repository-local GitHub CLI configuration when configured. If auth is unavailable, stop and ask the human to configure it instead of silently using unrelated global credentials.\n"
