from __future__ import annotations

from pathlib import Path

from .io import append_jsonl, ensure_dir, read_toml, write_toml
from .logger import append_event
from .paths import legacy_process_path, mailbox_dir, process_amendments_path, process_dir, process_flow_path, process_metadata_path, run_dir
from .time import now_iso
from .workflow import DEFAULT_FLOW, write_default_flow


PROCESS_KINDS = {"workspace", "virtual"}


def process_path(root: str | Path, goal_id: str, run_id: str, process_id: str) -> Path:
    return process_metadata_path(root, goal_id, run_id, process_id)


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
    process_kind: str = "workspace",
    extra: dict | None = None,
) -> Path:
    if process_kind not in PROCESS_KINDS:
        raise ValueError(f"invalid process kind {process_kind!r}; expected workspace or virtual")
    workspace = Path(workspace_path or root).resolve() if process_kind == "workspace" else None
    pdir = process_dir(root, goal_id, run_id, process_id)
    ensure_dir(pdir)
    data = {
        "process_id": process_id,
        "process_kind": process_kind,
        "role": role,
        "status": "active",
        "parent_process_id": parent_process_id,
        "workspace_path": str(workspace) if workspace else "",
        "state_path": str(pdir),
        "branch": "",
        "worktree_path": str(workspace) if workspace else "",
        "agent_substrate": "codex-goal",
        "agent_session_id": agent_session_id,
        "tmux_session": tmux_session,
        "workflow_state": "",
        "started_at": now_iso(),
        "last_heartbeat_at": now_iso(),
        "replaces": "",
        "adapter": {},
        "runtime": {"managed_by_local_supervisor": False, "session_handle": ""},
    }
    if extra:
        for key, value in extra.items():
            if isinstance(value, dict) and isinstance(data.get(key), dict):
                data[key].update(value)
            else:
                data[key] = value
    if data.get("process_kind") not in PROCESS_KINDS:
        raise ValueError(f"invalid process kind {data.get('process_kind')!r}; expected workspace or virtual")
    _ensure_mailbox(root, goal_id, run_id, process_id)
    _ensure_process_flow(root, goal_id, run_id, process_id, parent_process_id)
    if not data.get("workflow_state"):
        flow = read_toml(process_flow_path(root, goal_id, run_id, process_id))
        data["workflow_state"] = flow.get("flow", {}).get("initial_state", "")
    process_amendments_path(root, goal_id, run_id, process_id).touch(exist_ok=True)
    path = process_metadata_path(root, goal_id, run_id, process_id)
    write_toml(path, data)
    # Compatibility for older tools/tests while process directories become canonical.
    write_toml(legacy_process_path(root, goal_id, run_id, process_id), data)
    append_event(root, goal_id, run_id, "process-events", "process_spawned", {"role": role, "parent_process_id": parent_process_id}, process_id=process_id)
    return path


def load_process(root: str | Path, goal_id: str, run_id: str, process_id: str) -> dict:
    path = process_metadata_path(root, goal_id, run_id, process_id)
    if path.exists():
        return read_toml(path)
    return read_toml(legacy_process_path(root, goal_id, run_id, process_id))


def write_process(root: str | Path, goal_id: str, run_id: str, process_id: str, data: dict) -> None:
    write_toml(process_metadata_path(root, goal_id, run_id, process_id), data)
    write_toml(legacy_process_path(root, goal_id, run_id, process_id), data)


def heartbeat(root: str | Path, goal_id: str, run_id: str, process_id: str) -> None:
    data = load_process(root, goal_id, run_id, process_id)
    data["last_heartbeat_at"] = now_iso()
    write_process(root, goal_id, run_id, process_id, data)
    append_event(root, goal_id, run_id, "process-events", "process_heartbeat", {}, process_id=process_id)


def interrupt(root: str | Path, goal_id: str, run_id: str, process_id: str, reason: str) -> None:
    data = load_process(root, goal_id, run_id, process_id)
    data["status"] = "interrupted"
    data["interrupted_at"] = now_iso()
    data["interrupt_reason"] = reason
    write_process(root, goal_id, run_id, process_id, data)
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
    write_process(root, goal_id, run_id, process_id, data)
    append_event(root, goal_id, run_id, "process-events", "agent_session_attached", {"old_session": old_session, "new_session": new_session}, process_id=process_id)
    from .report import generate_agent_brief, generate_report

    generate_agent_brief(root, goal_id, run_id, process_id)
    generate_report(root, goal_id, run_id)


def record_flow_amendment(
    root: str | Path,
    goal_id: str,
    run_id: str,
    owner_process_id: str,
    target_process_id: str,
    reason: str,
    risk_class: str = "normal",
    evidence_refs: list[str] | None = None,
    approval_refs: list[str] | None = None,
    flow_patch_ref: str = "",
) -> dict:
    dangerous = risk_class in {
        "secrets_auth",
        "destructive_git",
        "irreversible_external",
        "acceptance_weakening",
        "human_gate_removal",
        "external_state_close",
        "git_destructive",
    }
    if dangerous and not approval_refs:
        event = append_event(
            root,
            goal_id,
            run_id,
            "process-events",
            "workflow_amendment_blocked",
            {"target_process_id": target_process_id, "reason": reason, "risk_class": risk_class, "requires_human_approval": True},
            process_id=owner_process_id,
        )
        return {"status": "blocked", "event": event, "requires_human_approval": True}
    record = {
        "amendment_id": f"amend_{len(_read_amendments(root, goal_id, run_id, target_process_id)) + 1:06d}",
        "owner_process_id": owner_process_id,
        "target_process_id": target_process_id,
        "reason": reason,
        "risk_class": risk_class,
        "requires_human_approval": dangerous,
        "approval_refs": approval_refs or [],
        "evidence_refs": evidence_refs or [],
        "flow_patch_ref": flow_patch_ref,
        "created_at": now_iso(),
    }
    append_jsonl(process_amendments_path(root, goal_id, run_id, target_process_id), record)
    event = append_event(root, goal_id, run_id, "process-events", "workflow_amendment_recorded", record, process_id=owner_process_id)
    return {"status": "recorded", "event": event, "amendment": record}


def _read_amendments(root: str | Path, goal_id: str, run_id: str, process_id: str) -> list[dict]:
    from .io import read_jsonl

    return read_jsonl(process_amendments_path(root, goal_id, run_id, process_id))


def _ensure_mailbox(root: str | Path, goal_id: str, run_id: str, process_id: str) -> None:
    mdir = mailbox_dir(root, goal_id, run_id, process_id)
    ensure_dir(mdir)
    for name in ["inbox.jsonl", "outbox.jsonl", "ack.jsonl"]:
        (mdir / name).touch(exist_ok=True)


def _ensure_process_flow(root: str | Path, goal_id: str, run_id: str, process_id: str, parent_process_id: str) -> None:
    dst = process_flow_path(root, goal_id, run_id, process_id)
    if dst.exists():
        return
    if parent_process_id:
        parent_flow = process_flow_path(root, goal_id, run_id, parent_process_id)
        if parent_flow.exists():
            write_toml(dst, read_toml(parent_flow))
            return
    run_flow = run_dir(root, goal_id, run_id) / "flow.snapshot.toml"
    if run_flow.exists():
        write_toml(dst, read_toml(run_flow))
        return
    write_toml(dst, DEFAULT_FLOW)
