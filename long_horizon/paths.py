from __future__ import annotations

from pathlib import Path

LH = ".long-horizon"


def root_path(root: str | Path) -> Path:
    return Path(root).resolve()


def lh_root(root: str | Path) -> Path:
    return root_path(root) / LH


def goal_dir(root: str | Path, goal_id: str) -> Path:
    return lh_root(root) / "goals" / goal_id


def run_dir(root: str | Path, goal_id: str, run_id: str) -> Path:
    return goal_dir(root, goal_id) / "runs" / run_id


def logs_dir(root: str | Path, goal_id: str, run_id: str) -> Path:
    return run_dir(root, goal_id, run_id) / "logs"


def reports_dir(root: str | Path, goal_id: str, run_id: str) -> Path:
    return run_dir(root, goal_id, run_id) / "reports"


def processes_dir(root: str | Path, goal_id: str, run_id: str) -> Path:
    return run_dir(root, goal_id, run_id) / "processes"


def process_dir(root: str | Path, goal_id: str, run_id: str, process_id: str) -> Path:
    return processes_dir(root, goal_id, run_id) / process_id


def process_metadata_path(root: str | Path, goal_id: str, run_id: str, process_id: str) -> Path:
    return process_dir(root, goal_id, run_id, process_id) / "process.toml"


def legacy_process_path(root: str | Path, goal_id: str, run_id: str, process_id: str) -> Path:
    return processes_dir(root, goal_id, run_id) / f"{process_id}.toml"


def process_flow_path(root: str | Path, goal_id: str, run_id: str, process_id: str) -> Path:
    return process_dir(root, goal_id, run_id, process_id) / "flow.toml"


def process_amendments_path(root: str | Path, goal_id: str, run_id: str, process_id: str) -> Path:
    return process_dir(root, goal_id, run_id, process_id) / "flow-amendments.jsonl"


def mailbox_dir(root: str | Path, goal_id: str, run_id: str, process_id: str) -> Path:
    return process_dir(root, goal_id, run_id, process_id) / "mailbox"


def boards_dir(root: str | Path, goal_id: str, run_id: str) -> Path:
    return run_dir(root, goal_id, run_id) / "boards"
