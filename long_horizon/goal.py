from __future__ import annotations

import shutil
from pathlib import Path

from .config import load_config
from .io import ensure_dir, read_text, write_text, write_toml
from .logger import append_event
from .paths import boards_dir, goal_dir, lh_root, processes_dir, reports_dir, run_dir
from .process import create_process
from .report import generate_agent_brief, generate_report
from .time import now_iso
from .workflow import DEFAULT_FLOW, allowed_next, write_default_flow


def create_goal(root: str | Path, goal_id: str, contract: str | Path) -> Path:
    gdir = goal_dir(root, goal_id)
    ensure_dir(gdir)
    contract_path = Path(contract)
    if contract_path.exists():
        shutil.copyfile(contract_path, gdir / "contract.md")
    else:
        write_text(gdir / "contract.md", str(contract))
    flow_path = gdir / "flow.toml"
    if not flow_path.exists():
        default_flow = lh_root(root) / "flows" / "default.toml"
        if default_flow.exists():
            shutil.copyfile(default_flow, flow_path)
        else:
            write_default_flow(flow_path)
    write_toml(gdir / "policy.snapshot.toml", load_config(root))
    return gdir


def create_run(root: str | Path, goal_id: str, run_id: str) -> Path:
    gdir = goal_dir(root, goal_id)
    if not gdir.exists():
        raise FileNotFoundError(f"missing goal {goal_id}")
    rdir = run_dir(root, goal_id, run_id)
    for rel in ["boards", "observer", "processes", "logs", "artifacts", "reports"]:
        ensure_dir(rdir / rel)
    shutil.copyfile(gdir / "flow.toml", rdir / "flow.snapshot.toml")
    from .io import read_toml

    flow = read_toml(rdir / "flow.snapshot.toml") if (rdir / "flow.snapshot.toml").exists() else DEFAULT_FLOW
    current = flow.get("flow", {}).get("initial_state", "understand")
    write_toml(
        boards_dir(root, goal_id, run_id) / "task.toml",
        {"current_state": current, "status": "active", "updated_at": now_iso(), "allowed_next": allowed_next(flow, current), "blockers": []},
    )
    write_toml(run_dir(root, goal_id, run_id) / "run.toml", {"run_id": run_id, "goal_id": goal_id, "status": "active", "created_at": now_iso()})
    write_toml(rdir / "observer" / "run-health.toml", {"status": "nominal", "drift_score": 0, "evidence_gaps": []})
    write_toml(rdir / "observer" / "watchdog.toml", {"alerts": []})
    write_toml(rdir / "observer" / "evidence-gaps.toml", {"gaps": []})
    _touch_ledgers(root, goal_id, run_id)
    create_process(root, goal_id, run_id, "primary", role="task", workspace_path=Path(root).resolve())
    append_event(root, goal_id, run_id, "process-events", "run_created", {"goal_id": goal_id}, process_id="primary")
    generate_agent_brief(root, goal_id, run_id, "primary")
    generate_report(root, goal_id, run_id)
    return rdir


def _touch_ledgers(root: str | Path, goal_id: str, run_id: str) -> None:
    for name in [
        "transitions.jsonl",
        "process-events.jsonl",
        "commands.jsonl",
        "artifacts.jsonl",
        "reviews.jsonl",
        "human.jsonl",
        "observer-events.jsonl",
        "reporter-annotations.jsonl",
        "notifications.jsonl",
        "loose.jsonl",
    ]:
        path = run_dir(root, goal_id, run_id) / "logs" / name
        ensure_dir(path.parent)
        path.touch(exist_ok=True)
    write_text(run_dir(root, goal_id, run_id) / "logs" / "timeline.md", "# Timeline\n\n## Generated Summary\n\n## Human Notes\n\n## Reporter Analysis\n")
