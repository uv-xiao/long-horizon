from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import ensure_dir, read_text, write_json, write_text
from .logger import append_event
from .paths import run_dir
from .time import now_iso


def propose_merge_repair(
    root: str | Path,
    goal_id: str,
    run_id: str,
    conflict_file: str,
    process_id: str = "merge-repair",
    strategy: str = "keep_both",
    approval_refs: list[str] | None = None,
    base_ref: str = "",
    parent_ref: str = "",
    child_ref: str = "",
    merge_failure_event_id: str = "",
    eval_refs: list[str] | None = None,
    source_note_refs: list[str] | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    path = Path(root) / conflict_file
    text = read_text(path)
    if "<<<<<<<" not in text or "=======" not in text or ">>>>>>>" not in text:
        raise ValueError("conflict_file does not contain conflict markers")
    markers = _conflict_markers(text)
    proposed = _resolve_conflict(text, strategy)
    repair_dir = ensure_dir(run_dir(root, goal_id, run_id) / "artifacts" / "merge-repair" / path.name)
    proposed_path = repair_dir / "proposed.txt"
    patch_path = repair_dir / "proposed.patch"
    write_text(proposed_path, proposed)
    write_text(patch_path, _proposed_patch(conflict_file, text, proposed))
    record = {
        "conflict_file": conflict_file,
        "strategy": strategy,
        "base_ref": base_ref,
        "parent_ref": parent_ref,
        "child_ref": child_ref,
        "merge_failure_event_id": merge_failure_event_id,
        "eval_refs": eval_refs or [],
        "source_note_refs": source_note_refs or [],
        "conflict_markers": markers,
        "proposed_text": str(proposed_path.relative_to(run_dir(root, goal_id, run_id))),
        "proposed_patch": str(patch_path.relative_to(run_dir(root, goal_id, run_id))),
        "apply_requested": apply,
        "approval_refs": approval_refs or [],
        "created_at": now_iso(),
        "status": "proposed",
    }
    if apply and not approval_refs:
        record["status"] = "blocked"
        record["reason"] = "dangerous merge application requires approval"
        write_json(repair_dir / "repair.json", record)
        event = append_event(root, goal_id, run_id, "reviews", "merge_repair_blocked", record, process_id=process_id)
        return {"status": "blocked", "record": record, "event": event}
    if apply:
        write_text(path, proposed)
        record["status"] = "applied"
    write_json(repair_dir / "repair.json", record)
    event = append_event(root, goal_id, run_id, "reviews", "merge_repair_proposed" if not apply else "merge_repair_applied", record, process_id=process_id)
    return {"status": record["status"], "record": record, "event": event}


def _resolve_conflict(text: str, strategy: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        if not lines[i].startswith("<<<<<<<"):
            out.append(lines[i])
            i += 1
            continue
        ours: list[str] = []
        theirs: list[str] = []
        i += 1
        while i < len(lines) and not lines[i].startswith("======="):
            ours.append(lines[i])
            i += 1
        i += 1
        while i < len(lines) and not lines[i].startswith(">>>>>>>"):
            theirs.append(lines[i])
            i += 1
        i += 1
        if strategy == "ours":
            out.extend(ours)
        elif strategy == "theirs":
            out.extend(theirs)
        else:
            out.extend(ours)
            for line in theirs:
                if line not in ours:
                    out.append(line)
    return "\n".join(out) + "\n"


def _conflict_markers(text: str) -> dict[str, list[str]]:
    lines = text.splitlines()
    markers = {"ours": [], "theirs": [], "headers": []}
    i = 0
    while i < len(lines):
        if not lines[i].startswith("<<<<<<<"):
            i += 1
            continue
        markers["headers"].append(lines[i])
        i += 1
        while i < len(lines) and not lines[i].startswith("======="):
            markers["ours"].append(lines[i])
            i += 1
        if i < len(lines):
            markers["headers"].append(lines[i])
            i += 1
        while i < len(lines) and not lines[i].startswith(">>>>>>>"):
            markers["theirs"].append(lines[i])
            i += 1
        if i < len(lines):
            markers["headers"].append(lines[i])
            i += 1
    return markers


def _proposed_patch(conflict_file: str, original: str, proposed: str) -> str:
    import difflib

    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            proposed.splitlines(keepends=True),
            fromfile=f"a/{conflict_file}",
            tofile=f"b/{conflict_file}",
        )
    )
