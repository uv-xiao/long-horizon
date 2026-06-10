from __future__ import annotations

from pathlib import Path

from .io import read_jsonl, read_toml, write_toml
from .logger import append_event
from .mailbox import read_mailbox
from .paths import boards_dir, process_flow_path, run_dir
from .process import load_process, write_process
from .time import now_iso
from .workflow import allowed_next, find_transition


def transition(root: str | Path, goal_id: str, run_id: str, process_id: str, to_state: str) -> dict:
    rdir = run_dir(root, goal_id, run_id)
    flow = _load_process_flow(root, goal_id, run_id, process_id)
    board_path = boards_dir(root, goal_id, run_id) / "task.toml"
    board = read_toml(board_path)
    current = board.get("current_state")
    event = append_event(root, goal_id, run_id, "transitions", "transition_requested", {"from": current, "to": to_state}, process_id=process_id)
    trans = find_transition(flow, current, to_state)
    if not trans:
        return _block(root, goal_id, run_id, process_id, current, to_state, ["transition is not allowed"], event["event_id"])
    reasons = _gate_reasons(root, goal_id, run_id, trans)
    if reasons:
        return _block(root, goal_id, run_id, process_id, current, to_state, reasons, event["event_id"])
    board["current_state"] = to_state
    board["updated_at"] = now_iso()
    board["allowed_next"] = allowed_next(flow, to_state)
    board["blockers"] = []
    write_toml(board_path, board)
    try:
        proc = load_process(root, goal_id, run_id, process_id)
        proc["workflow_state"] = to_state
        proc["updated_at"] = now_iso()
        write_process(root, goal_id, run_id, process_id, proc)
    except FileNotFoundError:
        pass
    applied = append_event(root, goal_id, run_id, "transitions", "transition_applied", {"from": current, "to": to_state}, process_id=process_id, causal_refs=[event["event_id"]])
    from .report import generate_report

    generate_report(root, goal_id, run_id)
    return {"status": "applied", "event": applied, "reasons": []}


def _block(root: str | Path, goal_id: str, run_id: str, process_id: str, current: str, to_state: str, reasons: list[str], request_id: str) -> dict:
    blocked = append_event(root, goal_id, run_id, "transitions", "transition_blocked", {"from": current, "to": to_state, "reasons": reasons}, process_id=process_id, causal_refs=[request_id])
    from .report import generate_report

    generate_report(root, goal_id, run_id)
    return {"status": "blocked", "event": blocked, "reasons": reasons}


def _gate_reasons(root: str | Path, goal_id: str, run_id: str, trans: dict) -> list[str]:
    reasons: list[str] = []
    rdir = run_dir(root, goal_id, run_id)
    for artifact in trans.get("requires_artifacts", []):
        if not (rdir / artifact).exists():
            reasons.append(f"missing artifact {artifact}")
    for check in trans.get("requires_checks", []):
        if not _check_passed(root, goal_id, run_id, check):
            reasons.append(f"missing passed check {check}")
    if trans.get("requires_human"):
        if not _human_gate_satisfied(root, goal_id, run_id, trans):
            reasons.append("missing human approval")
    for message_req in trans.get("requires_messages", []):
        if not _message_requirement_satisfied(root, goal_id, run_id, message_req):
            reasons.append(f"missing message {message_req}")
    for wait in trans.get("requires_waits", []):
        # Minimal v1: explicit wait checks can be satisfied by process status events.
        if not _wait_satisfied(root, goal_id, run_id, wait):
            reasons.append(f"wait not satisfied {wait}")
    return reasons


def _load_process_flow(root: str | Path, goal_id: str, run_id: str, process_id: str) -> dict:
    path = process_flow_path(root, goal_id, run_id, process_id)
    if path.exists():
        return read_toml(path)
    return read_toml(run_dir(root, goal_id, run_id) / "flow.snapshot.toml")


def _check_passed(root: str | Path, goal_id: str, run_id: str, check: str) -> bool:
    for event in read_jsonl(run_dir(root, goal_id, run_id) / "logs" / "commands.jsonl"):
        payload = event.get("payload", {})
        if payload.get("check_id") == check and payload.get("status") == "passed":
            return True
    return False


def _human_gate_satisfied(root: str | Path, goal_id: str, run_id: str, trans: dict) -> bool:
    gate = trans.get("human_gate", trans.get("to", ""))
    for event in read_jsonl(run_dir(root, goal_id, run_id) / "logs" / "human.jsonl"):
        payload = event.get("payload", {})
        if payload.get("classification") in {"approval", "approved"} and (gate in payload.get("target_refs", []) or not payload.get("target_refs")):
            return True
    return False


def _message_requirement_satisfied(root: str | Path, goal_id: str, run_id: str, requirement: str | dict) -> bool:
    if isinstance(requirement, str):
        target_process_id = "primary"
        message_type = requirement
    else:
        target_process_id = str(requirement.get("target_process_id", "primary"))
        message_type = str(requirement.get("message_type", requirement.get("type", "")))
    for message in read_mailbox(root, goal_id, run_id, target_process_id, "inbox"):
        if not message_type or message.get("message_type") == message_type:
            return True
    return False


def _wait_satisfied(root: str | Path, goal_id: str, run_id: str, wait: str) -> bool:
    for event in read_jsonl(run_dir(root, goal_id, run_id) / "logs" / "process-events.jsonl"):
        if event.get("event_type") == "process_completed" and wait in event.get("payload", {}).get("wait_refs", [wait]):
            return True
    return False
