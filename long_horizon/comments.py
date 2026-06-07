from __future__ import annotations

import json
from pathlib import Path

from .io import ensure_dir, read_json, write_text
from .logger import append_event
from .paths import lh_root, run_dir


def inbox_dir(root: str | Path) -> Path:
    return lh_root(root) / "inbox" / "comments"


def import_comments(root: str | Path, goal_id: str, run_id: str) -> list[dict]:
    ensure_dir(inbox_dir(root))
    imported: list[dict] = []
    seen = _seen_external_ids(root, goal_id, run_id)
    for path in sorted(inbox_dir(root).glob("*.json")):
        envelope = read_json(path)
        key = f"{envelope.get('channel')}:{envelope.get('external_comment_id')}"
        if key in seen:
            path.unlink()
            continue
        body = envelope.get("body", "")
        body_ref = envelope.get("body_ref")
        if len(body) > 1000:
            artifact = run_dir(root, goal_id, run_id) / "artifacts" / "human-comments" / f"{envelope.get('external_comment_id')}.md"
            write_text(artifact, body)
            body_ref = str(artifact.relative_to(run_dir(root, goal_id, run_id)))
            body = ""
        event = append_event(
            root,
            goal_id,
            run_id,
            "human",
            "human_comment",
            {
                "comment_id": key,
                "origin": envelope.get("channel", "local"),
                "author": envelope.get("author", ""),
                "external_thread_id": envelope.get("external_thread_id", ""),
                "external_comment_id": envelope.get("external_comment_id", ""),
                "body": body,
                "body_ref": body_ref,
                "target_refs": envelope.get("target_refs", []),
                "classification": _classify(body),
                "status": "open",
            },
            process_id="interaction-observer",
            actor="human-comment-importer",
        )
        append_event(root, goal_id, run_id, "notifications", "comment_imported", {"comment_id": key, "target_refs": envelope.get("target_refs", [])}, process_id="interaction-observer")
        imported.append(event)
        path.unlink()
    if imported:
        from .report import generate_report

        generate_report(root, goal_id, run_id)
    return imported


def _seen_external_ids(root: str | Path, goal_id: str, run_id: str) -> set[str]:
    from .io import read_jsonl

    seen: set[str] = set()
    for event in read_jsonl(run_dir(root, goal_id, run_id) / "logs" / "human.jsonl"):
        comment_id = event.get("payload", {}).get("comment_id")
        if comment_id:
            seen.add(comment_id)
    return seen


def _classify(body: str) -> str:
    low = body.lower()
    if "approve" in low or "yes" == low.strip():
        return "approval"
    if "reject" in low or "request change" in low:
        return "request_change"
    if "?" in body:
        return "question"
    return "note"
