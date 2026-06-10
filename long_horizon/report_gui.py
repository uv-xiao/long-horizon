from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import write_json
from .logger import append_event
from .paths import reports_dir
from .time import now_iso


def write_report_gui_manifest(root: str | Path, goal_id: str, run_id: str, adapter: str = "static-html") -> dict[str, Any]:
    manifest = {
        "adapter": adapter,
        "boundary": "report-data-json",
        "data": "report-data.json",
        "views": ["progress.html", "progress.md"],
        "compatible_adapter_targets": ["omp-oh-my-pi", "warp-style", "custom-frontend"],
        "created_at": now_iso(),
    }
    path = reports_dir(root, goal_id, run_id) / "report-gui-manifest.json"
    write_json(path, manifest)
    event = append_event(root, goal_id, run_id, "reporter-annotations", "report_gui_manifest_written", {"path": "reports/report-gui-manifest.json", **manifest}, process_id="reporter")
    return {"manifest": manifest, "path": str(path), "event": event}
