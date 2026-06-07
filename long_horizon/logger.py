from __future__ import annotations

import fcntl
import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .ids import count_jsonl, next_numeric_id
from .io import append_jsonl, ensure_dir, read_jsonl
from .paths import logs_dir
from .time import now_iso
from .validators import validate_event

LEDGERS = {
    "transitions": "transitions.jsonl",
    "process-events": "process-events.jsonl",
    "commands": "commands.jsonl",
    "artifacts": "artifacts.jsonl",
    "reviews": "reviews.jsonl",
    "human": "human.jsonl",
    "observer-events": "observer-events.jsonl",
    "reporter-annotations": "reporter-annotations.jsonl",
    "notifications": "notifications.jsonl",
}


def ledger_path(root: str | Path, goal_id: str, run_id: str, ledger: str) -> Path:
    if ledger not in LEDGERS:
        raise ValueError(f"unknown ledger {ledger}")
    return logs_dir(root, goal_id, run_id) / LEDGERS[ledger]


def append_event(
    root: str | Path,
    goal_id: str,
    run_id: str,
    ledger: str,
    event_type: str,
    payload: dict[str, Any],
    process_id: str = "primary",
    actor: str | None = None,
    source_refs: list[str] | None = None,
    causal_refs: list[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    path = ledger_path(root, goal_id, run_id, ledger)
    ensure_dir(path.parent)
    with _locked(path):
        prior = read_jsonl(path)
        prev_hash = prior[-1].get("event_hash") if prior else None
        seq = len(prior) + 1
        event = {
            "event_id": next_numeric_id("evt", _count_all_events(path.parent)),
            "event_type": event_type,
            "run_id": run_id,
            "process_id": process_id,
            "actor": actor or f"process:{process_id}",
            "ledger": ledger,
            "seq": seq,
            "created_at": now_iso(),
            "observed_at": None,
            "source_refs": source_refs or [],
            "causal_refs": causal_refs or [],
            "payload": payload,
            "prev_hash": prev_hash,
        }
        errors = validate_event(event)
        if errors:
            raise ValueError("; ".join(errors))
        event["event_hash"] = _hash_event(event)
        append_jsonl(path, event)
        return event


def append_loose(
    root: str | Path,
    goal_id: str,
    run_id: str,
    body: str,
    process_id: str = "primary",
    tags: list[str] | None = None,
    source_refs: list[str] | None = None,
) -> dict[str, Any]:
    path = logs_dir(root, goal_id, run_id) / "loose.jsonl"
    record = {
        "loose_id": next_numeric_id("loose", count_jsonl(path)),
        "created_at": now_iso(),
        "process_id": process_id,
        "tags": tags or [],
        "body": body,
        "source_refs": source_refs or [],
        "promotion_status": "unpromoted",
    }
    append_jsonl(path, record)
    return record


def _count_all_events(log_dir: Path) -> int:
    total = 0
    for name in LEDGERS.values():
        total += count_jsonl(log_dir / name)
    return total


def _hash_event(event: dict[str, Any]) -> str:
    canonical = dict(event)
    canonical.pop("event_hash", None)
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@contextmanager
def _locked(path: Path) -> Iterator[None]:
    lock_path = path.with_suffix(path.suffix + ".lock")
    ensure_dir(lock_path.parent)
    with lock_path.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
