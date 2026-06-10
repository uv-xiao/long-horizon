from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .io import ensure_dir, read_jsonl, write_json
from .logger import LEDGERS, _hash_event, append_event, ledger_path
from .paths import run_dir
from .time import now_iso


def reconcile_ledger(root: str | Path, goal_id: str, run_id: str, ledger: str, process_id: str = "ledger-recovery") -> dict[str, Any]:
    if ledger not in LEDGERS:
        raise ValueError("unknown ledger")
    path = ledger_path(root, goal_id, run_id, ledger)
    records = read_jsonl(path)
    issues = _ledger_issues(records)
    recovery_dir = ensure_dir(run_dir(root, goal_id, run_id) / "artifacts" / "ledger-recovery" / ledger)
    damaged_copy = recovery_dir / "damaged.jsonl"
    if path.exists():
        shutil.copy2(path, damaged_copy)
    reconciled = []
    prev_hash = None
    for idx, event in enumerate(records, start=1):
        fixed = dict(event)
        fixed["seq"] = idx
        fixed["prev_hash"] = prev_hash
        fixed.pop("event_hash", None)
        fixed["event_hash"] = _hash_event(fixed)
        prev_hash = fixed["event_hash"]
        reconciled.append(fixed)
    reconciled_path = recovery_dir / "reconciled.jsonl"
    reconciled_path.write_text("".join(__import__("json").dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in reconciled), encoding="utf-8")
    report = {
        "ledger": ledger,
        "issues": issues,
        "damaged_copy": str(damaged_copy.relative_to(run_dir(root, goal_id, run_id))),
        "reconciled_copy": str(reconciled_path.relative_to(run_dir(root, goal_id, run_id))),
        "mode": "preserve_and_reconcile",
        "created_at": now_iso(),
    }
    write_json(recovery_dir / "report.json", report)
    event = append_event(root, goal_id, run_id, "reviews", "ledger_reconciled", report, process_id=process_id)
    return {"report": report, "event": event}


def _ledger_issues(records: list[dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    prev_hash = None
    last_seq = 0
    for event in records:
        if int(event.get("seq", 0)) <= last_seq:
            issues.append(f"non-increasing seq at {event.get('event_id')}")
        last_seq = int(event.get("seq", 0))
        if event.get("prev_hash") != prev_hash:
            issues.append(f"prev_hash mismatch at {event.get('event_id')}")
        expected = _hash_event({k: v for k, v in event.items() if k != "event_hash"})
        if event.get("event_hash") != expected:
            issues.append(f"event_hash mismatch at {event.get('event_id')}")
        prev_hash = event.get("event_hash")
    return issues
