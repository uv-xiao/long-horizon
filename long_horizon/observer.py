from __future__ import annotations

from pathlib import Path

from .logger import append_event
from .process import create_process


def create_observer(root: str | Path, goal_id: str, run_id: str, process_id: str, observe_targets: list[str], steer_targets: list[str] | None = None, attached_process_id: str = "primary") -> Path:
    return create_process(
        root,
        goal_id,
        run_id,
        process_id,
        role="observer",
        extra={
            "attached_process_id": attached_process_id,
            "observe_targets": observe_targets,
            "observe_channels": ["state_files", "artifacts", "ledgers", "reports", "process_metadata", "tmux_capture"],
            "steer_targets": steer_targets or [],
            "steer_channels": ["tmux_input", "agent_thread_message", "brief_update"],
            "write_scope": "observer_only",
        },
    )


def record_intervention(root: str | Path, goal_id: str, run_id: str, observer_id: str, target_process_id: str, message: str, trigger_refs: list[str] | None = None) -> dict:
    requested = append_event(
        root,
        goal_id,
        run_id,
        "observer-events",
        "intervention_requested",
        {"target_process_id": target_process_id, "message": message, "trigger_refs": trigger_refs or []},
        process_id=observer_id,
        source_refs=trigger_refs or [],
    )
    delivered = append_event(
        root,
        goal_id,
        run_id,
        "observer-events",
        "intervention_delivered",
        {"target_process_id": target_process_id, "delivery_channel": "brief_update", "delivery_result": "recorded", "message": message},
        process_id=observer_id,
        causal_refs=[requested["event_id"]],
    )
    from .report import generate_report

    generate_report(root, goal_id, run_id)
    return delivered
