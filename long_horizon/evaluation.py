from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .io import ensure_dir, read_text, write_json
from .logger import append_event
from .paths import run_dir
from .time import now_iso


def run_evaluation(
    root: str | Path,
    goal_id: str,
    run_id: str,
    eval_id: str,
    adapter: str,
    process_id: str = "primary",
    command: str | None = None,
    file_path: str | None = None,
    contains: str | None = None,
    metric_name: str | None = None,
    metric_value: float | None = None,
    threshold: float | None = None,
) -> dict[str, Any]:
    if adapter not in {"command", "file_contains", "metric_threshold"}:
        raise ValueError("unknown evaluation adapter")
    result: dict[str, Any] = {"eval_id": eval_id, "adapter": adapter, "created_at": now_iso(), "status": "failed"}
    if adapter == "command":
        if not command:
            raise ValueError("command evaluation requires command")
        proc = subprocess.run(command, cwd=root, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result.update({"command": command, "exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr, "status": "passed" if proc.returncode == 0 else "failed"})
    elif adapter == "file_contains":
        if not file_path or contains is None:
            raise ValueError("file_contains evaluation requires file_path and contains")
        text = read_text(Path(root) / file_path)
        result.update({"file_path": file_path, "contains": contains, "status": "passed" if contains in text else "failed"})
    else:
        if metric_name is None or metric_value is None or threshold is None:
            raise ValueError("metric_threshold evaluation requires metric_name, metric_value, and threshold")
        result.update({"metric_name": metric_name, "metric_value": metric_value, "threshold": threshold, "status": "passed" if metric_value >= threshold else "failed"})
    artifact = ensure_dir(run_dir(root, goal_id, run_id) / "artifacts" / "evaluations") / f"{eval_id}.json"
    write_json(artifact, result)
    event = append_event(root, goal_id, run_id, "artifacts", "evaluation_recorded", {"path": _rel(root, artifact), "status": result["status"], "adapter": adapter}, process_id=process_id)
    if adapter == "command":
        append_event(root, goal_id, run_id, "commands", "evaluation_command_ran", {"eval_id": eval_id, "command": command, "status": result["status"]}, process_id=process_id)
    return {"evaluation": result, "artifact": str(artifact), "event": event}


def _rel(root: str | Path, path: Path) -> str:
    return str(path.resolve().relative_to(Path(root).resolve()))
