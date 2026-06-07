from __future__ import annotations

from pathlib import Path

from .io import read_toml, write_toml
from .logger import append_event
from .paths import processes_dir
from .time import now_iso


def process_path(root: str | Path, goal_id: str, run_id: str, process_id: str) -> Path:
    return processes_dir(root, goal_id, run_id) / f"{process_id}.toml"


def create_process(
    root: str | Path,
    goal_id: str,
    run_id: str,
    process_id: str,
    role: str = "task",
    workspace_path: str | Path | None = None,
    parent_process_id: str = "",
    agent_session_id: str = "",
    tmux_session: str = "",
    extra: dict | None = None,
) -> Path:
    workspace = Path(workspace_path or root).resolve()
    data = {
        "process_id": process_id,
        "role": role,
        "status": "active",
        "parent_process_id": parent_process_id,
        "workspace_path": str(workspace),
        "state_path": str(workspace / ".long-horizon"),
        "branch": "",
        "worktree_path": str(workspace),
        "agent_substrate": "codex-goal",
        "agent_session_id": agent_session_id,
        "tmux_session": tmux_session,
        "started_at": now_iso(),
        "last_heartbeat_at": now_iso(),
        "replaces": "",
    }
    if extra:
        data.update(extra)
    path = process_path(root, goal_id, run_id, process_id)
    write_toml(path, data)
    append_event(root, goal_id, run_id, "process-events", "process_spawned", {"role": role, "parent_process_id": parent_process_id}, process_id=process_id)
    return path


def load_process(root: str | Path, goal_id: str, run_id: str, process_id: str) -> dict:
    return read_toml(process_path(root, goal_id, run_id, process_id))


def heartbeat(root: str | Path, goal_id: str, run_id: str, process_id: str) -> None:
    data = load_process(root, goal_id, run_id, process_id)
    data["last_heartbeat_at"] = now_iso()
    write_toml(process_path(root, goal_id, run_id, process_id), data)
    append_event(root, goal_id, run_id, "process-events", "process_heartbeat", {}, process_id=process_id)


def interrupt(root: str | Path, goal_id: str, run_id: str, process_id: str, reason: str) -> None:
    data = load_process(root, goal_id, run_id, process_id)
    data["status"] = "interrupted"
    data["interrupted_at"] = now_iso()
    data["interrupt_reason"] = reason
    write_toml(process_path(root, goal_id, run_id, process_id), data)
    append_event(root, goal_id, run_id, "process-events", "agent_session_lost", {"reason": reason, "old_session": data.get("agent_session_id", "")}, process_id=process_id)
    append_event(root, goal_id, run_id, "process-events", "process_interrupted", {"reason": reason}, process_id=process_id)
    from .report import generate_agent_brief, generate_report

    generate_agent_brief(root, goal_id, run_id, process_id)
    generate_report(root, goal_id, run_id)


def resume(root: str | Path, goal_id: str, run_id: str, process_id: str, new_session: str) -> None:
    data = load_process(root, goal_id, run_id, process_id)
    old_session = data.get("agent_session_id", "")
    data["status"] = "active"
    data["agent_session_id"] = new_session
    data["resumed_at"] = now_iso()
    data["last_heartbeat_at"] = now_iso()
    write_toml(process_path(root, goal_id, run_id, process_id), data)
    append_event(root, goal_id, run_id, "process-events", "agent_session_attached", {"old_session": old_session, "new_session": new_session}, process_id=process_id)
    from .report import generate_agent_brief, generate_report

    generate_agent_brief(root, goal_id, run_id, process_id)
    generate_report(root, goal_id, run_id)
