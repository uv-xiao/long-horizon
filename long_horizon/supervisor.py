from __future__ import annotations

import os
import shlex
import signal
import subprocess
from pathlib import Path
from typing import Any

from .io import ensure_dir, read_json, read_toml, write_json
from .logger import append_event
from .paths import run_dir
from .process import create_process, load_process, process_path, write_process
from .time import now_iso


def start_supervised_process(
    root: str | Path,
    goal_id: str,
    run_id: str,
    process_id: str,
    command: str | list[str],
    cwd: str | Path | None = None,
    role: str = "task",
    restart_policy: str = "never",
) -> dict[str, Any]:
    if restart_policy not in {"never", "on_failure"}:
        raise ValueError("restart_policy must be never or on_failure")
    if not process_path(root, goal_id, run_id, process_id).exists():
        create_process(root, goal_id, run_id, process_id, role=role, workspace_path=cwd or root)
    proc = load_process(root, goal_id, run_id, process_id)
    artifact_dir = ensure_dir(run_dir(root, goal_id, run_id) / "artifacts" / "supervisor" / process_id)
    stdout_path = artifact_dir / "stdout.log"
    stderr_path = artifact_dir / "stderr.log"
    args = command if isinstance(command, list) else shlex.split(command)
    stdout = stdout_path.open("ab")
    stderr = stderr_path.open("ab")
    child = subprocess.Popen(args, cwd=str(cwd or root), stdout=stdout, stderr=stderr)
    stdout.close()
    stderr.close()
    handle = {
        "pid": child.pid,
        "command": args,
        "cwd": str(Path(cwd or root).resolve()),
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "restart_policy": restart_policy,
        "started_at": now_iso(),
        "status": "running",
    }
    write_json(_handle_path(root, goal_id, run_id, process_id), handle)
    proc.setdefault("runtime", {})
    proc["runtime"].update(
        {
            "managed_by_local_supervisor": True,
            "session_handle": str(_handle_path(root, goal_id, run_id, process_id)),
            "pid": child.pid,
            "restart_policy": restart_policy,
        }
    )
    proc["status"] = "active"
    write_process(root, goal_id, run_id, process_id, proc)
    event = append_event(root, goal_id, run_id, "process-events", "supervisor_process_started", handle, process_id=process_id)
    return {"handle": handle, "event": event}


def supervised_status(root: str | Path, goal_id: str, run_id: str, process_id: str) -> dict[str, Any]:
    handle = read_json(_handle_path(root, goal_id, run_id, process_id))
    pid = int(handle["pid"])
    running = _pid_running(pid)
    handle["status"] = "running" if running else handle.get("status", "exited")
    write_json(_handle_path(root, goal_id, run_id, process_id), handle)
    return handle


def reap_supervised_process(root: str | Path, goal_id: str, run_id: str, process_id: str) -> dict[str, Any]:
    handle = read_json(_handle_path(root, goal_id, run_id, process_id))
    pid = int(handle["pid"])
    exit_code: int | None = None
    try:
        waited_pid, status = os.waitpid(pid, os.WNOHANG)
        if waited_pid == 0:
            return {"handle": supervised_status(root, goal_id, run_id, process_id), "event": None}
        exit_code = os.waitstatus_to_exitcode(status)
    except ChildProcessError:
        if _pid_running(pid):
            return {"handle": supervised_status(root, goal_id, run_id, process_id), "event": None}
    handle["status"] = "exited"
    handle["exit_code"] = exit_code
    handle["finished_at"] = now_iso()
    write_json(_handle_path(root, goal_id, run_id, process_id), handle)
    proc = load_process(root, goal_id, run_id, process_id)
    proc["status"] = "completed" if exit_code in {0, None} else "failed"
    write_process(root, goal_id, run_id, process_id, proc)
    event = append_event(root, goal_id, run_id, "process-events", "supervisor_process_exited", handle, process_id=process_id)
    if exit_code not in {0, None} and handle.get("restart_policy") == "on_failure":
        restart = start_supervised_process(root, goal_id, run_id, process_id, handle["command"], cwd=handle["cwd"], restart_policy="on_failure")
        handle["restart_event_id"] = restart["event"]["event_id"]
    return {"handle": handle, "event": event}


def terminate_supervised_process(root: str | Path, goal_id: str, run_id: str, process_id: str) -> dict[str, Any]:
    handle = read_json(_handle_path(root, goal_id, run_id, process_id))
    pid = int(handle["pid"])
    if _pid_running(pid):
        os.kill(pid, signal.SIGTERM)
    handle["status"] = "terminating"
    handle["terminated_at"] = now_iso()
    write_json(_handle_path(root, goal_id, run_id, process_id), handle)
    event = append_event(root, goal_id, run_id, "process-events", "supervisor_process_terminated", handle, process_id=process_id)
    return {"handle": handle, "event": event}


def _handle_path(root: str | Path, goal_id: str, run_id: str, process_id: str) -> Path:
    return run_dir(root, goal_id, run_id) / "artifacts" / "supervisor" / process_id / "handle.json"


def _pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True
