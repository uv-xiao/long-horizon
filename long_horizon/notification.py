from __future__ import annotations

from pathlib import Path
from typing import Any

from .github_adapter import ensure_github_process, record_github_operation
from .io import ensure_dir, write_json
from .logger import append_event
from .mailbox import send_message
from .paths import run_dir
from .process import create_process, process_path
from .time import now_iso


def send_notification(
    root: str | Path,
    goal_id: str,
    run_id: str,
    channel: str,
    subject: str,
    body: str,
    target_process_id: str = "primary",
    github_target: str = "issue",
    number: int | None = None,
    execute: bool = False,
) -> dict[str, Any]:
    process_id = f"notify-{channel}"
    if channel == "github":
        ensure_github_process(root, goal_id, run_id, process_id)
    elif not process_path(root, goal_id, run_id, process_id).exists():
        create_process(root, goal_id, run_id, process_id, role="notification", process_kind="virtual", extra={"adapter": {"type": channel}})
    payload = {
        "channel": channel,
        "subject": subject,
        "body": body,
        "target_process_id": target_process_id,
        "created_at": now_iso(),
        "status": "planned",
    }
    if channel == "github":
        op = "comment_pr" if github_target == "pr" else "comment_issue"
        payload["github_operation"] = record_github_operation(
            root,
            goal_id,
            run_id,
            op,
            github_target,
            title=subject,
            body=body,
            number=number,
            process_id=process_id,
            target_process_id=target_process_id,
            execute=execute,
        )["operation"]
    artifact = _artifact_path(root, goal_id, run_id, channel, subject)
    write_json(artifact, payload)
    message = send_message(root, goal_id, run_id, process_id, target_process_id, f"notification_{channel}", body, artifact_refs=[_rel(root, artifact)])
    event = append_event(root, goal_id, run_id, "notifications", "notification_sent", {**payload, "artifact": _rel(root, artifact), "message_id": message["message_id"]}, process_id=process_id)
    return {"notification": payload, "artifact": str(artifact), "message": message, "event": event}


def _artifact_path(root: str | Path, goal_id: str, run_id: str, channel: str, subject: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in subject.lower()).strip("-") or "notification"
    return ensure_dir(run_dir(root, goal_id, run_id) / "artifacts" / "notifications") / f"{channel}-{safe}.json"


def _rel(root: str | Path, path: Path) -> str:
    return str(path.resolve().relative_to(Path(root).resolve()))
