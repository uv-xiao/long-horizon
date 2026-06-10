from __future__ import annotations

import gzip
from pathlib import Path
from typing import Any

from .io import ensure_dir, write_json
from .logger import append_event
from .paths import run_dir
from .time import now_iso


def run_retention_sidecar(
    root: str | Path,
    goal_id: str,
    run_id: str,
    min_bytes: int = 1,
    process_id: str = "retention",
) -> dict[str, Any]:
    artifacts = run_dir(root, goal_id, run_id) / "artifacts"
    retention_dir = ensure_dir(artifacts / "retention")
    records: list[dict[str, Any]] = []
    for path in sorted(artifacts.rglob("*")):
        if not path.is_file() or retention_dir in path.parents:
            continue
        if path.stat().st_size < min_bytes:
            continue
        rel = path.relative_to(artifacts)
        out = retention_dir / f"{rel.as_posix().replace('/', '__')}.gz"
        with path.open("rb") as src, gzip.open(out, "wb") as dst:
            dst.write(src.read())
        record = {
            "source": str(path.relative_to(run_dir(root, goal_id, run_id))),
            "compressed": str(out.relative_to(run_dir(root, goal_id, run_id))),
            "source_size": path.stat().st_size,
            "compressed_size": out.stat().st_size,
            "policy": "compress_copy",
            "created_at": now_iso(),
        }
        records.append(record)
        append_event(root, goal_id, run_id, "artifacts", "artifact_retained", record, process_id=process_id)
    manifest = retention_dir / "manifest.json"
    write_json(manifest, {"records": records, "created_at": now_iso()})
    return {"manifest": str(manifest), "records": records}
