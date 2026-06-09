from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import validate_config
from .io import read_jsonl, read_toml
from .paths import boards_dir, lh_root, logs_dir, process_flow_path, processes_dir, run_dir
from .workflow import state_ids


EVENT_REQUIRED = {"event_id", "event_type", "run_id", "process_id", "actor", "ledger", "seq", "created_at", "source_refs", "causal_refs", "payload"}


def validate_flow(flow: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ids = state_ids(flow)
    if not ids:
        errors.append("flow has no states")
    initial = flow.get("flow", {}).get("initial_state")
    if initial not in ids:
        errors.append(f"initial state {initial!r} is not declared")
    for transition in flow.get("transitions", []):
        if transition.get("from") not in ids:
            errors.append(f"transition from unknown state {transition.get('from')!r}")
        if transition.get("to") not in ids:
            errors.append(f"transition to unknown state {transition.get('to')!r}")
    if len(ids) != len(flow.get("states", [])):
        errors.append("duplicate state ids")
    return errors


def validate_event(event: dict[str, Any]) -> list[str]:
    errors = [f"missing event field {key}" for key in sorted(EVENT_REQUIRED - set(event))]
    if "seq" in event and not isinstance(event["seq"], int):
        errors.append("seq must be integer")
    if "source_refs" in event and not isinstance(event["source_refs"], list):
        errors.append("source_refs must be list")
    if "causal_refs" in event and not isinstance(event["causal_refs"], list):
        errors.append("causal_refs must be list")
    if "payload" in event and not isinstance(event["payload"], dict):
        errors.append("payload must be object")
    return errors


def validate_run(root: str | Path, goal_id: str, run_id: str) -> list[str]:
    errors: list[str] = []
    rdir = run_dir(root, goal_id, run_id)
    if not rdir.exists():
        return [f"missing run {goal_id}/{run_id}"]
    flow = read_toml(process_flow_path(root, goal_id, run_id, "primary")) if process_flow_path(root, goal_id, run_id, "primary").exists() else read_toml(rdir / "flow.snapshot.toml")
    errors.extend(validate_flow(flow))
    board = read_toml(boards_dir(root, goal_id, run_id) / "task.toml")
    if board.get("current_state") not in state_ids(flow):
        errors.append("board current_state is not in flow snapshot")
    proc_paths = list(processes_dir(root, goal_id, run_id).glob("*/process.toml"))
    seen = {path.parent.name for path in proc_paths}
    proc_paths.extend(path for path in processes_dir(root, goal_id, run_id).glob("*.toml") if path.stem not in seen)
    for proc in proc_paths:
        data = read_toml(proc)
        for key in ["process_id", "role", "status", "workspace_path", "state_path"]:
            if key not in data:
                errors.append(f"{proc.name} missing {key}")
        if data.get("process_kind", "workspace") not in {"workspace", "virtual"}:
            errors.append(f"{proc.name} invalid process_kind {data.get('process_kind')!r}")
        process_id = str(data.get("process_id", proc.parent.name if proc.name == "process.toml" else proc.stem))
        pflow = process_flow_path(root, goal_id, run_id, process_id)
        if pflow.exists():
            errors.extend(f"{process_id}/flow.toml: {err}" for err in validate_flow(read_toml(pflow)))
    for ledger in logs_dir(root, goal_id, run_id).glob("*.jsonl"):
        if ledger.name == "loose.jsonl":
            continue
        last_seq = 0
        for event in read_jsonl(ledger):
            errors.extend(f"{ledger.name}: {err}" for err in validate_event(event))
            seq = event.get("seq", 0)
            if isinstance(seq, int) and seq <= last_seq:
                errors.append(f"{ledger.name}: non-increasing seq")
            if isinstance(seq, int):
                last_seq = seq
    return errors


def validate_root(root: str | Path, goal_id: str | None = None, run_id: str | None = None) -> list[str]:
    errors = validate_config(root)
    if not lh_root(root).exists():
        errors.append("missing .long-horizon")
    if goal_id and run_id:
        errors.extend(validate_run(root, goal_id, run_id))
    return errors
