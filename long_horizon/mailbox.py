from __future__ import annotations

from pathlib import Path
from typing import Any

from .ids import count_jsonl, next_numeric_id
from .io import append_jsonl, read_jsonl
from .logger import append_event
from .paths import mailbox_dir
from .time import now_iso


def mailbox_file(root: str | Path, goal_id: str, run_id: str, process_id: str, name: str) -> Path:
    if name not in {"inbox", "outbox", "ack"}:
        raise ValueError(f"unknown mailbox file {name!r}")
    path = mailbox_dir(root, goal_id, run_id, process_id) / f"{name}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    return path


def send_message(
    root: str | Path,
    goal_id: str,
    run_id: str,
    source_process_id: str,
    target_process_id: str,
    message_type: str,
    body: str,
    artifact_refs: list[str] | None = None,
    causal_refs: list[str] | None = None,
    requires_ack: bool = False,
    deliver: bool = True,
) -> dict[str, Any]:
    outbox = mailbox_file(root, goal_id, run_id, source_process_id, "outbox")
    message = {
        "message_id": next_numeric_id("msg", _count_messages(root, goal_id, run_id)),
        "source_process_id": source_process_id,
        "target_process_id": target_process_id,
        "message_type": message_type,
        "body": body,
        "artifact_refs": artifact_refs or [],
        "causal_refs": causal_refs or [],
        "requires_ack": requires_ack,
        "created_at": now_iso(),
    }
    append_jsonl(outbox, {**message, "mailbox": "outbox", "delivery_status": "pending"})
    append_event(
        root,
        goal_id,
        run_id,
        "notifications",
        "message_sent",
        {"message": message},
        process_id=source_process_id,
        causal_refs=causal_refs or [],
    )
    if deliver:
        deliver_message(root, goal_id, run_id, message)
    return message


def deliver_message(root: str | Path, goal_id: str, run_id: str, message: dict[str, Any]) -> dict[str, Any]:
    inbox = mailbox_file(root, goal_id, run_id, str(message["target_process_id"]), "inbox")
    delivered = {**message, "mailbox": "inbox", "delivery_status": "delivered", "delivered_at": now_iso()}
    append_jsonl(inbox, delivered)
    append_event(
        root,
        goal_id,
        run_id,
        "notifications",
        "message_delivered",
        {"message": delivered},
        process_id=str(message["source_process_id"]),
        causal_refs=list(message.get("causal_refs", [])),
    )
    return delivered


def ack_message(
    root: str | Path,
    goal_id: str,
    run_id: str,
    process_id: str,
    message_id: str,
    status: str = "acknowledged",
    body: str = "",
) -> dict[str, Any]:
    record = {
        "message_id": message_id,
        "process_id": process_id,
        "status": status,
        "body": body,
        "created_at": now_iso(),
    }
    append_jsonl(mailbox_file(root, goal_id, run_id, process_id, "ack"), record)
    append_event(root, goal_id, run_id, "notifications", "message_acknowledged", record, process_id=process_id)
    return record


def read_mailbox(root: str | Path, goal_id: str, run_id: str, process_id: str, name: str = "inbox") -> list[dict[str, Any]]:
    return read_jsonl(mailbox_file(root, goal_id, run_id, process_id, name))


def collect_mailboxes(root: str | Path, goal_id: str, run_id: str, process_ids: list[str]) -> dict[str, dict[str, list[dict[str, Any]]]]:
    return {
        process_id: {
            "inbox": read_mailbox(root, goal_id, run_id, process_id, "inbox"),
            "outbox": read_mailbox(root, goal_id, run_id, process_id, "outbox"),
            "ack": read_mailbox(root, goal_id, run_id, process_id, "ack"),
        }
        for process_id in process_ids
    }


def _count_messages(root: str | Path, goal_id: str, run_id: str) -> int:
    base = Path(root).resolve() / ".long-horizon" / "goals" / goal_id / "runs" / run_id / "processes"
    total = 0
    for path in base.glob("*/mailbox/outbox.jsonl"):
        total += count_jsonl(path)
    return total
