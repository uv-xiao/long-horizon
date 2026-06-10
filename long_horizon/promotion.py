from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import ensure_dir, read_text, write_json, write_text
from .logger import append_event
from .paths import lh_root, run_dir
from .time import now_iso


DESTINATIONS = {
    "skill": lambda root, name: Path(root) / ".agents" / "skills" / name / "SKILL.md",
    "rule": lambda root, name: Path(root) / ".agents" / "rules" / f"{name}.md",
    "memory": lambda root, name: lh_root(root) / "memory" / f"{name}.md",
    "adapter": lambda root, name: Path(root) / ".agents" / "adapters" / f"{name}.md",
}


def promote_artifact(
    root: str | Path,
    goal_id: str,
    run_id: str,
    kind: str,
    name: str,
    source_artifact: str,
    process_id: str = "primary",
    approval_refs: list[str] | None = None,
    risk_class: str = "normal",
) -> dict[str, Any]:
    if kind not in DESTINATIONS:
        raise ValueError("kind must be skill, rule, memory, or adapter")
    dangerous = risk_class in {"shared_agent_behavior", "secrets_auth", "destructive_git"}
    if dangerous and not approval_refs:
        event = append_event(root, goal_id, run_id, "reviews", "promotion_blocked", {"kind": kind, "name": name, "risk_class": risk_class}, process_id=process_id)
        return {"status": "blocked", "event": event}
    src = run_dir(root, goal_id, run_id) / source_artifact
    content = read_text(src)
    _validate_promotion_evidence(content)
    dst = DESTINATIONS[kind](root, name)
    write_text(dst, content)
    review_artifact = ensure_dir(run_dir(root, goal_id, run_id) / "artifacts" / "deposition") / f"{kind}-{name}.json"
    record = {
        "kind": kind,
        "name": name,
        "source_artifact": source_artifact,
        "destination": str(dst),
        "approval_refs": approval_refs or [],
        "risk_class": risk_class,
        "promoted_at": now_iso(),
        "rollback": f"remove or revert {dst}",
    }
    write_json(review_artifact, record)
    event = append_event(root, goal_id, run_id, "reviews", "promotion_applied", {**record, "review_artifact": _rel(root, review_artifact)}, process_id=process_id)
    return {"status": "applied", "destination": str(dst), "review_artifact": str(review_artifact), "event": event}


def _validate_promotion_evidence(content: str) -> None:
    required = ["problem", "evidence", "scope", "validation", "rollback"]
    missing = [word for word in required if word not in content.lower()]
    if missing:
        raise ValueError("promotion artifact missing sections: " + ", ".join(missing))


def _rel(root: str | Path, path: Path) -> str:
    return str(path.resolve().relative_to(Path(root).resolve()))
