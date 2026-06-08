from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from .io import copy_file, write_json
from .logger import append_event
from .paths import lh_root, run_dir
from .process import create_process
from .time import now_iso


def spawn_child_worktree(
    root: str | Path,
    goal_id: str,
    run_id: str,
    parent_process_id: str,
    process_id: str,
    branch: str,
    worktree_path: str | Path,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    child_path = Path(worktree_path).resolve()
    _run_git(root_path, "rev-parse", "--show-toplevel")
    if child_path.exists() and any(child_path.iterdir()):
        raise ValueError(f"worktree path is not empty: {child_path}")
    _run_git(root_path, "worktree", "add", "-b", branch, str(child_path), "HEAD")

    parent_process = create_process(
        root_path,
        goal_id,
        run_id,
        process_id,
        role="task",
        workspace_path=child_path,
        parent_process_id=parent_process_id,
        extra={"branch": branch, "worktree_path": str(child_path), "state_path": str(child_path / ".long-horizon")},
    )
    manifest = _snapshot_manifest(root_path, goal_id, run_id, process_id, branch, child_path)
    manifest_rel = Path("artifacts") / "snapshots" / f"{process_id}.manifest.json"
    write_json(run_dir(root_path, goal_id, run_id) / manifest_rel, manifest)
    _copy_long_horizon_state(root_path, child_path)
    write_json(run_dir(child_path, goal_id, run_id) / manifest_rel, manifest)
    append_event(
        root_path,
        goal_id,
        run_id,
        "artifacts",
        "worktree_state_copied",
        {"child_process_id": process_id, "branch": branch, "worktree_path": str(child_path), "manifest": str(manifest_rel)},
        process_id=parent_process_id,
    )
    return {
        "worktree_path": str(child_path),
        "branch": branch,
        "parent_process_path": parent_process,
        "manifest": manifest,
    }


def import_child_state(
    root: str | Path,
    goal_id: str,
    run_id: str,
    child_worktree_path: str | Path,
    child_process_id: str,
    artifact_paths: list[str],
    target_process_id: str = "primary",
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    child_path = Path(child_worktree_path).resolve()
    copied: list[str] = []
    for rel in artifact_paths:
        clean_rel = Path(rel)
        if clean_rel.is_absolute() or ".." in clean_rel.parts:
            raise ValueError(f"unsafe artifact path: {rel}")
        src = run_dir(child_path, goal_id, run_id) / clean_rel
        if not src.exists():
            raise FileNotFoundError(src)
        dst_rel = Path("artifacts") / "imports" / child_process_id / clean_rel.name
        copy_file(src, run_dir(root_path, goal_id, run_id) / dst_rel)
        copied.append(str(dst_rel))
        append_event(
            root_path,
            goal_id,
            run_id,
            "artifacts",
            "artifact_imported",
            {
                "artifact_id": f"{child_process_id}:{clean_rel}",
                "from_process_id": child_process_id,
                "target_process_id": target_process_id,
                "path": str(dst_rel),
                "source_worktree": str(child_path),
            },
            process_id=target_process_id,
        )
    manifest_rel = Path("artifacts") / "imports" / child_process_id / "import-manifest.json"
    manifest = {
        "imported_at": now_iso(),
        "child_process_id": child_process_id,
        "child_worktree_path": str(child_path),
        "target_process_id": target_process_id,
        "copied_artifacts": copied,
    }
    write_json(run_dir(root_path, goal_id, run_id) / manifest_rel, manifest)
    return manifest


def merge_child_branch(
    root: str | Path,
    goal_id: str,
    run_id: str,
    child_process_id: str,
    branch: str,
    target_process_id: str = "primary",
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    before = _run_git(root_path, "rev-parse", "HEAD").strip()
    proc = subprocess.run(
        ["git", "merge", "--no-ff", "--no-edit", branch],
        cwd=root_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        append_event(
            root_path,
            goal_id,
            run_id,
            "process-events",
            "child_branch_merge_failed",
            {
                "child_process_id": child_process_id,
                "branch": branch,
                "target_process_id": target_process_id,
                "before_head": before,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            },
            process_id=target_process_id,
        )
        return {"status": "failed", "branch": branch, "stdout": proc.stdout, "stderr": proc.stderr}
    after = _run_git(root_path, "rev-parse", "HEAD").strip()
    append_event(
        root_path,
        goal_id,
        run_id,
        "process-events",
        "child_branch_merged",
        {
            "child_process_id": child_process_id,
            "branch": branch,
            "target_process_id": target_process_id,
            "before_head": before,
            "after_head": after,
        },
        process_id=target_process_id,
    )
    return {"status": "merged", "branch": branch, "before_head": before, "after_head": after}


def _copy_long_horizon_state(root: Path, child_path: Path) -> None:
    src = lh_root(root)
    dst = lh_root(child_path)
    if not src.exists():
        raise FileNotFoundError(src)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _snapshot_manifest(root: Path, goal_id: str, run_id: str, process_id: str, branch: str, child_path: Path) -> dict[str, Any]:
    return {
        "created_at": now_iso(),
        "goal_id": goal_id,
        "run_id": run_id,
        "process_id": process_id,
        "branch": branch,
        "parent_root": str(root),
        "worktree_path": str(child_path),
        "copy_policy": "copy-all-long-horizon-state",
        "parent_head": _run_git(root, "rev-parse", "HEAD").strip(),
    }


def _run_git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.stdout
