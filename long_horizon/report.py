from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .capabilities import load_capabilities
from .config import load_config
from .io import read_jsonl, read_toml, write_json, write_text
from .mailbox import collect_mailboxes
from .paths import boards_dir, process_amendments_path, process_flow_path, process_metadata_path, processes_dir, reports_dir, run_dir
from .workflow import allowed_next


def generate_report(root: str | Path, goal_id: str, run_id: str) -> dict[str, Any]:
    data = build_report_data(root, goal_id, run_id)
    rdir = reports_dir(root, goal_id, run_id)
    write_json(rdir / "report-data.json", data)
    write_text(rdir / "progress.md", render_markdown(data))
    write_text(rdir / "progress.html", render_html(data))
    return data


def build_report_data(root: str | Path, goal_id: str, run_id: str) -> dict[str, Any]:
    rdir = run_dir(root, goal_id, run_id)
    board = read_toml(boards_dir(root, goal_id, run_id) / "task.toml")
    flow = _primary_flow(root, goal_id, run_id)
    processes = [_process_node(path, board, root, goal_id, run_id) for path in _process_metadata_paths(root, goal_id, run_id)]
    events = _unified_events(rdir)
    mailboxes = collect_mailboxes(root, goal_id, run_id, [str(proc["process_id"]) for proc in processes])
    mailbox_messages = _mailbox_messages(mailboxes)
    amendments = _workflow_amendments(root, goal_id, run_id, processes)
    edges = _communication_edges(events, processes, mailbox_messages)
    initial_state = flow.get("flow", {}).get("initial_state", board.get("current_state"))
    snapshots = [_snapshot_at(events[: idx + 1], processes, initial_state, idx) for idx in range(len(events))]
    workflow = _workflow_projection(flow, board, events)
    timeline = _timeline_projection(events, processes, edges, snapshots, workflow)
    capabilities = load_capabilities(root)
    config = load_config(root)
    data = {
        "goal_id": goal_id,
        "run_id": run_id,
        "feature_settings": config.get("features", {}),
        "profile": config.get("profile", {}),
        "responsibility_map": config.get("responsibility", {}),
        "operation_mode": capabilities.get("analysis", {}).get("operation_mode", "runtime-owned"),
        "agent_capabilities": capabilities,
        "current_state": board.get("current_state"),
        "allowed_next": board.get("allowed_next", allowed_next(flow, board.get("current_state", ""))),
        "playback": {"axis": "event_sequence", "count": len(events), "current_index": max(0, len(events) - 1)},
        "processes": processes,
        "mailboxes": mailboxes,
        "mailbox_messages": mailbox_messages,
        "workflow_amendments": amendments,
        "mechanism_evidence": _mechanism_evidence(rdir, events),
        "events": events,
        "event_lanes": _event_lanes(events),
        "communication_edges": edges,
        "human_comments": _human_comments(events),
        "observer_interventions": _observer_interventions(events),
        "snapshots": snapshots,
        "timeline": timeline,
        "anchors": _unique_anchors(_anchors(events, processes, edges) + _timeline_anchors(timeline)),
    }
    return data


def generate_agent_brief(root: str | Path, goal_id: str, run_id: str, process_id: str = "primary") -> Path:
    rdir = run_dir(root, goal_id, run_id)
    board = read_toml(boards_dir(root, goal_id, run_id) / "task.toml")
    capabilities = load_capabilities(root)
    mode = capabilities.get("analysis", {}).get("operation_mode", "runtime-owned")
    mode_details = capabilities.get("mode", {})
    process_path = processes_dir(root, goal_id, run_id) / f"{process_id}.toml"
    canonical_process_path = process_metadata_path(root, goal_id, run_id, process_id)
    proc = read_toml(canonical_process_path) if canonical_process_path.exists() else read_toml(process_path) if process_path.exists() else {"process_id": process_id, "status": "unknown"}
    events = _unified_events(rdir)
    observer_messages = [
        event
        for event in events
        if event["event_type"].startswith("intervention_") and event.get("payload", {}).get("target_process_id") == process_id
    ]
    recovery = ""
    if proc.get("status") == "interrupted":
        recovery = f"\n## Recovery Context\n\nThis process is interrupted. Reason: {proc.get('interrupt_reason', '')}. Attach a replacement executor to the same workspace/state root, then run `process resume`.\n"
    content = f"""# Agent Brief

Process: `{process_id}`
Role: `{proc.get('role', '')}`
Status: `{proc.get('status', '')}`
Operation mode: `{mode}`
Profile: `{load_config(root).get('profile', {}).get('label', '')}`
Workspace: `{proc.get('workspace_path', '')}`
State root: `{proc.get('state_path', '')}`

## Operation Mode Responsibilities

Template owns:
{_brief_items(mode_details.get('template_responsibilities', []))}

Native agent owns:
{_brief_items(mode_details.get('native_agent_responsibilities', []))}

## Workflow

Current state: `{board.get('current_state')}`
Allowed next: {', '.join(board.get('allowed_next', [])) or '(none)'}
Blockers: {', '.join(board.get('blockers', [])) or '(none)'}
{recovery}
## Targeted Observer Messages

{_brief_observer_messages(observer_messages)}

## Commands

```bash
python -m long_horizon validate --root . --goal-id {goal_id} --run-id {run_id}
python -m long_horizon transition --root . --goal-id {goal_id} --run-id {run_id} --process-id {process_id} --to <state>
python -m long_horizon report generate --root . --goal-id {goal_id} --run-id {run_id}
```

Workflow boards advance only through the transition tool. Canonical ledgers are append-only.
"""
    path = reports_dir(root, goal_id, run_id) / "agent-brief.md"
    write_text(path, content)
    return path


def render_markdown(data: dict[str, Any]) -> str:
    recent = data["events"][-8:]
    lines = [
        "# Long-Horizon Progress",
        "",
        f"Goal: `{data['goal_id']}`",
        f"Run: `{data['run_id']}`",
        f"Operation mode: `{data.get('operation_mode', '')}`",
        f"Feature profile: `{data.get('profile', {}).get('label', '')}`",
        f"Current state: `{data['current_state']}`",
        f"Allowed next: {', '.join(data['allowed_next']) or '(none)'}",
        "",
        "## Processes",
    ]
    for proc in data["processes"]:
        lines.append(f"- `{proc['process_id']}` {proc.get('process_kind', '')} {proc['role']} {proc['status']} at `{proc['workflow_state']}`")
    lines.extend(["", "## Mailboxes"])
    for message in data.get("mailbox_messages", [])[-8:]:
        lines.append(f"- `{message['message_id']}` `{message['message_type']}` `{message['source_process_id']}` -> `{message['target_process_id']}`")
    lines.extend(["", "## Recent Events"])
    for event in recent:
        lines.append(f"- `{event['event_id']}` `{event['event_type']}` from `{event['process_id']}`")
    lines.extend(["", "## Mechanism Evidence"])
    for name, evidence in sorted(data.get("mechanism_evidence", {}).items()):
        event_count = len(evidence.get("events", []))
        artifact_count = len(evidence.get("artifacts", []))
        lines.append(f"- `{name}`: {event_count} events, {artifact_count} artifacts")
    lines.extend(["", "## Report", "", "Open `progress.html` for the timeline report, message links, event details, and selected-state workflow diagram."])
    return "\n".join(lines) + "\n"


def _brief_items(items: list[str]) -> str:
    if not items:
        return "- (none)"
    return "\n".join(f"- {item}" for item in items)


def _human_summary_html(comments: list[dict[str, Any]]) -> str:
    if not comments:
        return "<p>(none)</p>"
    return "<ul>" + "".join(
        f"<li><strong>{html.escape(str(comment.get('classification', '')))}</strong> "
        f"{html.escape(str(comment.get('author', '')))}: {html.escape(str(comment.get('body', '')))}</li>"
        for comment in comments
    ) + "</ul>"


def _observer_summary_html(interventions: list[dict[str, Any]]) -> str:
    if not interventions:
        return "<p>(none)</p>"
    return "<ul>" + "".join(
        f"<li><strong>{html.escape(str(item.get('observer_process_id', '')))}</strong> -> "
        f"{html.escape(str(item.get('target_process_id', '')))}: {html.escape(str(item.get('message', '')))}</li>"
        for item in interventions
    ) + "</ul>"


def _json_script_payload(data: dict[str, Any]) -> str:
    return (
        json.dumps(data, ensure_ascii=False)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )


def _timeline_html(data: dict[str, Any]) -> str:
    timeline = data["timeline"]
    lanes = timeline.get("lanes", [])
    markers = timeline.get("event_markers", [])
    messages = timeline.get("messages", [])
    lane_index = {lane["lane_id"]: idx for idx, lane in enumerate(lanes)}
    label_width = 180
    step = 96
    lane_height = 68
    event_count = max(1, len(data.get("events", [])))
    width = max(860, label_width + event_count * step + 80)
    height = 28 + max(1, len(lanes)) * lane_height
    marker_by_lane: dict[str, list[dict[str, Any]]] = {}
    for marker in markers:
        marker_by_lane.setdefault(marker["lane_id"], []).append(marker)
    parts = [
        f'<div class="perfetto-timeline" id="timeline"><div class="timeline-canvas" style="width:{width}px;height:{height}px">',
        '<div class="timeline-axis">',
    ]
    for idx in range(event_count):
        x = label_width + idx * step + 8
        parts.append(f'<span class="tick" style="left:{x}px">#{idx}</span>')
    parts.append("</div>")
    parts.append(_message_layer_svg(messages, lane_index, label_width, step, lane_height, width, height - 28))
    for row, lane in enumerate(lanes):
        top = 28 + row * lane_height
        lane_id = html.escape(str(lane["lane_id"]))
        label = html.escape(str(lane.get("label", lane["lane_id"])))
        role = html.escape(str(lane.get("role", lane.get("kind", ""))))
        parts.append(f'<div class="timeline-lane" id="{lane_id}" style="top:{top}px;width:{width}px">')
        parts.append(f'<div class="timeline-lane-label">{label}<span class="lane-role">{role}</span></div><div class="lane-track"></div>')
        for segment in lane.get("state_segments", []):
            left = label_width + int(segment["start_index"]) * step + 8
            seg_width = max(42, (int(segment["end_index"]) - int(segment["start_index"]) + 1) * step - 12)
            state = html.escape(str(segment.get("state", "")))
            status = html.escape(str(segment.get("status", "")))
            segment_id = html.escape(str(segment["segment_id"]))
            parts.append(
                f'<button class="timeline-state-segment status-{status}" id="{segment_id}" '
                f'data-segment-id="{segment_id}" style="left:{left}px;width:{seg_width}px" '
                f'title="{state} / {status}">{state}</button>'
            )
        for marker in marker_by_lane.get(lane["lane_id"], []):
            left = label_width + int(marker["event_index"]) * step + 42
            event_id = html.escape(str(marker["event_id"]))
            label_text = html.escape(str(marker.get("label", marker.get("event_type", ""))))
            kind = _marker_class(marker)
            parts.append(
                f'<button class="timeline-event-marker {kind}" id="event-{event_id}" data-event-id="{event_id}" '
                f'style="left:{left}px" title="{label_text}">{label_text}</button>'
            )
        parts.append("</div>")
    parts.append("</div></div>")
    return "".join(parts)


def _message_layer_svg(
    messages: list[dict[str, Any]],
    lane_index: dict[str, int],
    label_width: int,
    step: int,
    lane_height: int,
    width: int,
    height: int,
) -> str:
    parts = [
        f'<svg class="timeline-message-layer" width="{width}" height="{height}" viewBox="0 0 {width} {height}" aria-label="timeline message links">',
        '<defs><marker id="timeline-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="#8b5e34"/></marker></defs>',
    ]
    for message in messages:
        from_row = lane_index.get(message.get("from_lane_id", ""))
        to_row = lane_index.get(message.get("to_lane_id", ""))
        if from_row is None or to_row is None:
            continue
        x1 = label_width + int(message.get("event_index", 0)) * step + 51
        x2 = x1 + 34
        y1 = from_row * lane_height + 52
        y2 = to_row * lane_height + 52
        if from_row == to_row:
            y_mid = max(12, y1 - 20)
            path = f"M{x1},{y1} C{x1 + 28},{y_mid} {x2 - 28},{y_mid} {x2},{y2}"
            label_x = x1 + 10
            label_y = y_mid - 4
        else:
            mid = (x1 + x2) / 2
            path = f"M{x1},{y1} C{mid},{y1} {mid},{y2} {x2},{y2}"
            label_x = mid + 4
            label_y = (y1 + y2) / 2 - 4
        message_id = html.escape(str(message["message_id"]))
        label = html.escape(str(message.get("kind", "message")))
        parts.append(
            f'<path class="timeline-message-link" id="{message_id}" data-message-id="{message_id}" d="{path}"></path>'
            f'<text class="timeline-message-label" x="{label_x:.1f}" y="{label_y:.1f}">{label}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _workflow_diagram_svg(workflow: dict[str, Any], selected_state: str) -> str:
    states = [dict(state) for state in workflow.get("states", [])]
    transitions = workflow.get("transitions", [])
    allowed = set(workflow.get("allowed_next", []))
    completed = set(workflow.get("completed_states", []))
    width = max(340, len(states) * 132 + 32)
    parts = [
        f'<svg viewBox="0 0 {width} 180" role="img" aria-label="state transition diagram">',
        '<defs><marker id="workflow-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="#1d4f8f"/></marker></defs>',
    ]
    by_id: dict[str, dict[str, Any]] = {}
    for idx, state in enumerate(states):
        state["_x"] = 18 + idx * 132
        state["_y"] = 56
        by_id[str(state["id"])] = state
    for transition in transitions:
        from_state = by_id.get(str(transition.get("from")))
        to_state = by_id.get(str(transition.get("to")))
        if not from_state or not to_state:
            continue
        cls = "workflow-edge allowed" if transition.get("from") == selected_state and transition.get("to") in allowed else "workflow-edge"
        parts.append(
            f'<line class="{cls}" x1="{from_state["_x"] + 104}" y1="{from_state["_y"] + 22}" '
            f'x2="{to_state["_x"]}" y2="{to_state["_y"] + 22}"></line>'
        )
    for state in states:
        state_id = str(state["id"])
        cls = "workflow-node selected" if state_id == selected_state else "workflow-node completed" if state_id in completed else "workflow-node"
        label = html.escape(state_id)
        parts.append(
            f'<rect class="{cls}" x="{state["_x"]}" y="{state["_y"]}" width="104" height="44" rx="5"></rect>'
            f'<text x="{state["_x"] + 8}" y="{state["_y"] + 26}">{label}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _marker_class(marker: dict[str, Any]) -> str:
    if marker.get("ledger") == "human":
        return "human"
    if marker.get("ledger") == "observer-events" or str(marker.get("event_type", "")).startswith("intervention"):
        return "observer"
    if marker.get("ledger") == "transitions":
        return "transition"
    return "event"


def render_html(data: dict[str, Any]) -> str:
    payload = _json_script_payload(data)
    static_timeline = _timeline_html(data)
    static_diagram = _workflow_diagram_svg(data["timeline"]["workflow"], str(data.get("current_state", "")))
    static_inspector = html.escape(json.dumps(data["events"][-1] if data["events"] else data, indent=2, ensure_ascii=False))
    human_summary = _human_summary_html(data.get("human_comments", []))
    observer_summary = _observer_summary_html(data.get("observer_interventions", []))
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>Long-Horizon Progress</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 0; color: #17202a; background: #f5f6f2; }}
header {{ padding: 16px 20px; background: #1f3a3d; color: white; }}
main {{ display: grid; grid-template-columns: minmax(0, 1fr) 380px; gap: 16px; padding: 16px; }}
section, aside {{ background: white; border: 1px solid #d8d8d2; border-radius: 6px; padding: 12px; }}
h2 {{ font-size: 16px; margin: 0 0 10px; }}
pre {{ white-space: pre-wrap; font-size: 12px; }}
.perfetto-timeline {{ overflow-x: auto; border: 1px solid #cfcfc8; border-radius: 6px; background: #fbfbf8; }}
.timeline-canvas {{ position: relative; min-height: 180px; }}
.timeline-axis {{ position: sticky; top: 0; height: 28px; background: #f1f2ee; border-bottom: 1px solid #d8d8d2; z-index: 4; }}
.tick {{ position: absolute; top: 5px; font-size: 11px; color: #69706b; }}
.timeline-lane {{ position: absolute; left: 0; height: 68px; border-bottom: 1px solid #e1e1dc; }}
.timeline-lane-label {{ position: absolute; left: 0; top: 0; bottom: 0; width: 180px; padding: 10px 8px; box-sizing: border-box; background: #ffffff; border-right: 1px solid #d8d8d2; z-index: 3; }}
.lane-role {{ display: block; font-size: 11px; color: #68736f; }}
.lane-track {{ position: absolute; left: 180px; right: 0; top: 0; bottom: 0; background: linear-gradient(90deg, rgba(31,58,61,0.08) 1px, transparent 1px); background-size: 96px 100%; }}
.timeline-state-segment {{ position: absolute; top: 10px; height: 24px; border: 1px solid #6a8d73; background: #dcebdd; border-radius: 4px; padding: 0 8px; font-size: 12px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; cursor: pointer; color: #193328; }}
.timeline-state-segment.status-interrupted {{ border-color: #b45309; background: #fde5c0; }}
.timeline-state-segment.status-completed {{ border-color: #4f7a8a; background: #d8ebf0; }}
.timeline-event-marker {{ position: absolute; top: 42px; width: 18px; height: 18px; transform: rotate(45deg); border: 1px solid #324c64; background: #edf3f8; cursor: pointer; text-indent: -999px; overflow: hidden; }}
.timeline-event-marker.observer {{ background: #fff0cc; border-color: #9a6b16; }}
.timeline-event-marker.human {{ background: #f4e5ff; border-color: #6b4c8a; }}
.timeline-event-marker.transition {{ background: #dbeafe; border-color: #315f9d; }}
.timeline-message-layer {{ position: absolute; left: 0; top: 28px; pointer-events: none; z-index: 2; }}
.timeline-message-link {{ fill: none; stroke: #8b5e34; stroke-width: 1.8; marker-end: url(#timeline-arrow); pointer-events: auto; cursor: pointer; }}
.timeline-message-label {{ fill: #5c4934; font-size: 11px; pointer-events: none; }}
.details-panel {{ min-height: 220px; }}
.state-transition-diagram svg {{ width: 100%; min-height: 170px; }}
.workflow-node {{ fill: #fdfdfb; stroke: #65756e; stroke-width: 1.2; }}
.workflow-node.selected {{ fill: #dbeafe; stroke: #1d4f8f; stroke-width: 2; }}
.workflow-node.completed {{ fill: #dcebdd; }}
.workflow-edge {{ stroke: #9a9a91; stroke-width: 1.3; marker-end: url(#workflow-arrow); }}
.workflow-edge.allowed {{ stroke: #1d4f8f; stroke-width: 2.2; }}
.summary-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 16px; }}
</style>
<header><h1>Long-Horizon Progress</h1><div>Goal {html.escape(data['goal_id'])} / Run {html.escape(data['run_id'])} / Mode {html.escape(str(data.get('operation_mode', '')))}</div></header>
<main>
  <section>
    <h2>Execution Timeline</h2>
    {static_timeline}
    <div class="summary-grid">
      <section>
        <h2>Human Comments</h2>
        <div id="human-comments">{human_summary}</div>
      </section>
      <section>
        <h2>Observer Interventions</h2>
        <div id="observer-interventions">{observer_summary}</div>
      </section>
    </div>
  </section>
  <aside>
    <h2>Selected Details</h2>
    <div class="state-transition-diagram" id="state-transition-diagram">{static_diagram}</div>
    <div class="details-panel"><pre id="inspector">{static_inspector}</pre></div>
  </aside>
</main>
<script id="report-data" type="application/json">{payload}</script>
<script>
const data = JSON.parse(document.getElementById('report-data').textContent);
const inspector = document.getElementById('inspector');
const diagram = document.getElementById('state-transition-diagram');
function inspect(kind, id) {{
  let obj = null;
  if (kind === 'event') obj = data.events.find(event => event.event_id === id);
  if (kind === 'message') obj = data.timeline.messages.find(message => message.message_id === id);
  if (kind === 'segment') {{
    for (const lane of data.timeline.lanes) {{
      obj = lane.state_segments.find(segment => segment.segment_id === id);
      if (obj) break;
    }}
    if (obj) diagram.innerHTML = workflowDiagram(obj.state);
  }}
  inspector.textContent = JSON.stringify(obj || data, null, 2);
}}
function workflowDiagram(selected) {{
  const workflow = data.timeline.workflow || {{states: [], transitions: [], allowed_next: []}};
  const states = workflow.states || [];
  const transitions = workflow.transitions || [];
  const allowed = new Set(workflow.allowed_next || []);
  const width = Math.max(340, states.length * 132 + 32);
  let svg = `<svg viewBox="0 0 ${{width}} 180" role="img" aria-label="state transition diagram"><defs><marker id="workflow-arrow-js" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="#1d4f8f"/></marker></defs>`;
  states.forEach((state, idx) => {{
    state._x = 18 + idx * 132; state._y = 56;
  }});
  transitions.forEach(t => {{
    const from = states.find(state => state.id === t.from), to = states.find(state => state.id === t.to);
    if (!from || !to) return;
    const cls = t.from === selected && allowed.has(t.to) ? 'workflow-edge allowed' : 'workflow-edge';
    svg += `<line class="${{cls}}" x1="${{from._x + 104}}" y1="${{from._y + 22}}" x2="${{to._x}}" y2="${{to._y + 22}}"></line>`;
  }});
  states.forEach(state => {{
    const cls = state.id === selected ? 'workflow-node selected' : 'workflow-node';
    svg += `<rect class="${{cls}}" x="${{state._x}}" y="${{state._y}}" width="104" height="44" rx="5"></rect><text x="${{state._x + 8}}" y="${{state._y + 26}}">${{state.id}}</text>`;
  }});
  return svg + '</svg>';
}}
document.querySelectorAll('.timeline-event-marker').forEach(el => el.addEventListener('click', () => inspect('event', el.dataset.eventId)));
document.querySelectorAll('.timeline-state-segment').forEach(el => el.addEventListener('click', () => inspect('segment', el.dataset.segmentId)));
document.querySelectorAll('.timeline-message-link').forEach(el => el.addEventListener('click', () => inspect('message', el.dataset.messageId)));
</script>
</html>
"""


def _process_metadata_paths(root: str | Path, goal_id: str, run_id: str) -> list[Path]:
    base = processes_dir(root, goal_id, run_id)
    paths = list(base.glob("*/process.toml"))
    seen = {path.parent.name for path in paths}
    for legacy in base.glob("*.toml"):
        if legacy.stem not in seen:
            paths.append(legacy)
    return sorted(paths, key=lambda p: (p.parent.name if p.name == "process.toml" else p.stem))


def _primary_flow(root: str | Path, goal_id: str, run_id: str) -> dict[str, Any]:
    path = process_flow_path(root, goal_id, run_id, "primary")
    if path.exists():
        return read_toml(path)
    return read_toml(run_dir(root, goal_id, run_id) / "flow.snapshot.toml")


def _mailbox_messages(mailboxes: dict[str, dict[str, list[dict[str, Any]]]]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for process_id, files in sorted(mailboxes.items()):
        for name in ["outbox", "inbox"]:
            for item in files.get(name, []):
                key = (str(item.get("message_id", "")), name)
                if key in seen:
                    continue
                seen.add(key)
                messages.append({**item, "process_id": process_id, "mailbox_file": name})
    messages.sort(key=lambda item: (str(item.get("created_at", "")), str(item.get("delivered_at", "")), str(item.get("message_id", "")), str(item.get("mailbox_file", ""))))
    return messages


def _workflow_amendments(root: str | Path, goal_id: str, run_id: str, processes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    amendments: list[dict[str, Any]] = []
    for proc in processes:
        process_id = str(proc.get("process_id", ""))
        for item in read_jsonl(process_amendments_path(root, goal_id, run_id, process_id)):
            amendments.append({**item, "process_id": process_id})
    return amendments


def _process_node(path: Path, board: dict[str, Any], root: str | Path, goal_id: str, run_id: str) -> dict[str, Any]:
    data = read_toml(path)
    process_id = str(data.get("process_id", path.parent.name if path.name == "process.toml" else path.stem))
    flow = read_toml(process_flow_path(root, goal_id, run_id, process_id)) if process_flow_path(root, goal_id, run_id, process_id).exists() else {}
    return {
        "process_id": process_id,
        "process_kind": data.get("process_kind", "workspace"),
        "role": data.get("role"),
        "status": data.get("status"),
        "workflow_state": data.get("workflow_state") or board.get("current_state"),
        "flow_id": flow.get("flow", {}).get("id", ""),
        "parent_process_id": data.get("parent_process_id", ""),
        "workspace_path": data.get("workspace_path", ""),
        "state_path": data.get("state_path", ""),
        "anchor": f"#process-{data.get('process_id')}",
    }


def _unified_events(rdir: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for ledger in sorted((rdir / "logs").glob("*.jsonl")):
        if ledger.name == "loose.jsonl":
            continue
        events.extend(read_jsonl(ledger))
    events.sort(key=lambda e: (e.get("created_at", ""), e.get("ledger", ""), e.get("seq", 0)))
    for idx, event in enumerate(events):
        event["event_index"] = idx
        event["anchor"] = f"#event-{event['event_id']}"
    return events


def _communication_edges(events: list[dict[str, Any]], processes: list[dict[str, Any]], mailbox_messages: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    process_ids = {p["process_id"] for p in processes}
    for proc in processes:
        if proc.get("parent_process_id"):
            spawn = next((e for e in events if e.get("event_type") == "process_spawned" and e.get("process_id") == proc["process_id"]), None)
            edges.append({"kind": "spawn", "from": proc["parent_process_id"], "to": proc["process_id"], "event_id": spawn.get("event_id") if spawn else f"spawn-{proc['process_id']}"})
    for event in events:
        payload = event.get("payload", {})
        target = payload.get("target_process_id")
        if event.get("event_type") == "artifact_imported" and payload.get("from_process_id") in process_ids and target in process_ids:
            edges.append({"kind": "artifact_import", "from": payload["from_process_id"], "to": target, "event_id": event["event_id"]})
            continue
        if event.get("event_type") in {"review_verdict", "plan_critique"} and target in process_ids:
            edges.append({"kind": "review_result", "from": event["process_id"], "to": target, "event_id": event["event_id"]})
            continue
        if target in process_ids and event.get("process_id") in process_ids:
            kind = "steer" if event["event_type"].startswith("intervention") else "message"
            edges.append({"kind": kind, "from": event["process_id"], "to": target, "event_id": event["event_id"]})
    for message in mailbox_messages or []:
        if message.get("source_process_id") in process_ids and message.get("target_process_id") in process_ids:
            edges.append(
                {
                    "kind": message.get("message_type", "mailbox_message"),
                    "from": message["source_process_id"],
                    "to": message["target_process_id"],
                    "event_id": message.get("message_id", ""),
                    "message_id": message.get("message_id", ""),
                }
            )
    return edges


def _snapshot_at(events: list[dict[str, Any]], processes: list[dict[str, Any]], initial_state: str, idx: int) -> dict[str, Any]:
    process_status = {proc["process_id"]: dict(proc) for proc in processes}
    current_state = initial_state
    for event in events:
        payload = event.get("payload", {})
        if event.get("event_type") == "transition_applied":
            current_state = payload.get("to", current_state)
        if event.get("event_type") in {"process_interrupted", "agent_session_lost"} and event.get("process_id") in process_status:
            process_status[event["process_id"]]["status"] = "interrupted"
        if event.get("event_type") == "agent_session_attached" and event.get("process_id") in process_status:
            process_status[event["process_id"]]["status"] = "active"
        if event.get("event_type") == "process_completed" and event.get("process_id") in process_status:
            process_status[event["process_id"]]["status"] = "completed"
    for proc in process_status.values():
        proc["workflow_state"] = current_state
    return {
        "event_index": idx,
        "current_state": current_state,
        "processes": list(process_status.values()),
        "visible_event_ids": [e["event_id"] for e in events],
    }


def _workflow_projection(flow: dict[str, Any], board: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    states = [{"id": str(state.get("id", "")), "kind": state.get("kind", "")} for state in flow.get("states", [])]
    if not states and board.get("current_state"):
        states = [{"id": str(board["current_state"]), "kind": "state"}]
    transitions = [
        {
            "from": str(transition.get("from", "")),
            "to": str(transition.get("to", "")),
            "requires_human": bool(transition.get("requires_human", False)),
            "human_gate": transition.get("human_gate", ""),
        }
        for transition in flow.get("transitions", [])
    ]
    completed: list[str] = []
    for event in events:
        if event.get("event_type") == "transition_applied":
            from_state = event.get("payload", {}).get("from")
            if from_state and from_state not in completed:
                completed.append(str(from_state))
    return {
        "flow_id": flow.get("flow", {}).get("id", ""),
        "initial_state": flow.get("flow", {}).get("initial_state", ""),
        "current_state": board.get("current_state", ""),
        "allowed_next": board.get("allowed_next", allowed_next(flow, board.get("current_state", ""))),
        "terminal_states": flow.get("flow", {}).get("terminal_states", []),
        "states": states,
        "transitions": transitions,
        "completed_states": completed,
    }


def _timeline_projection(
    events: list[dict[str, Any]],
    processes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    snapshots: list[dict[str, Any]],
    workflow: dict[str, Any],
) -> dict[str, Any]:
    process_ids = {str(process.get("process_id")) for process in processes}
    lanes = []
    for process in _ordered_processes(processes):
        lane_id = f"process:{process['process_id']}"
        lanes.append(
            {
                "lane_id": lane_id,
                "kind": "process",
                "label": str(process.get("process_id", "")),
                "role": str(process.get("role", "")),
                "process_id": str(process.get("process_id", "")),
                "parent_process_id": str(process.get("parent_process_id", "")),
                "state_segments": _state_segments_for_process(process, snapshots, lane_id, events),
            }
        )
    event_markers = []
    for event in events:
        lane_id = _event_lane_id(event, process_ids)
        if not any(lane["lane_id"] == lane_id for lane in lanes):
            lanes.append({"lane_id": lane_id, "kind": "system", "label": _lane_label(lane_id), "role": "event channel", "state_segments": []})
        event_markers.append(
            {
                "event_id": event["event_id"],
                "event_index": event.get("event_index", 0),
                "event_type": event.get("event_type", ""),
                "ledger": event.get("ledger", ""),
                "lane_id": lane_id,
                "label": f"{event.get('event_index', 0)} {event.get('event_type', '')}",
                "anchor": f"#event-{event['event_id']}",
            }
        )
    messages = _timeline_messages(events, edges, process_ids)
    return {"axis": "event_sequence", "workflow": workflow, "lanes": lanes, "event_markers": event_markers, "messages": messages}


def _ordered_processes(processes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(processes, key=lambda p: (0 if p.get("process_id") == "primary" else 1, str(p.get("parent_process_id", "")), str(p.get("process_id", ""))))


def _state_segments_for_process(
    process: dict[str, Any],
    snapshots: list[dict[str, Any]],
    lane_id: str,
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    process_id = str(process.get("process_id", ""))
    if not snapshots:
        return [
            {
                "segment_id": f"state-{process_id}-0",
                "lane_id": lane_id,
                "process_id": process_id,
                "state": process.get("workflow_state", ""),
                "status": process.get("status", ""),
                "start_index": 0,
                "end_index": 0,
                "anchor": "#state-at-0",
            }
        ]
    segments: list[dict[str, Any]] = []
    current_state = None
    current_status = None
    start_index = 0
    for snapshot in snapshots:
        projected = next((item for item in snapshot.get("processes", []) if str(item.get("process_id")) == process_id), process)
        state = str(projected.get("workflow_state", snapshot.get("current_state", "")))
        status = str(projected.get("status", process.get("status", "")))
        idx = int(snapshot.get("event_index", 0))
        if current_state is None:
            current_state = state
            current_status = status
            start_index = idx
            continue
        if state != current_state or status != current_status:
            segments.append(_state_segment(process_id, lane_id, current_state, current_status or "", start_index, idx - 1, events))
            current_state = state
            current_status = status
            start_index = idx
    end_index = int(snapshots[-1].get("event_index", 0))
    segments.append(_state_segment(process_id, lane_id, current_state or "", current_status or "", start_index, end_index, events))
    return segments


def _state_segment(
    process_id: str,
    lane_id: str,
    state: str,
    status: str,
    start_index: int,
    end_index: int,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    safe_state = str(state).replace(" ", "-")
    return {
        "segment_id": f"state-{process_id}-{start_index}-{end_index}-{safe_state}",
        "lane_id": lane_id,
        "process_id": process_id,
        "state": state,
        "status": status,
        "start_index": start_index,
        "end_index": max(start_index, end_index),
        "start_event_id": events[start_index]["event_id"] if events and start_index < len(events) else "",
        "end_event_id": events[end_index]["event_id"] if events and end_index < len(events) else "",
        "anchor": f"#state-at-{start_index}",
    }


def _event_lane_id(event: dict[str, Any], process_ids: set[str]) -> str:
    process_id = str(event.get("process_id", ""))
    if process_id in process_ids:
        return f"process:{process_id}"
    ledger = event.get("ledger", "")
    if ledger == "human":
        return "human"
    if ledger == "notifications":
        return "system:notifications"
    if ledger == "reporter-annotations":
        return "system:reporter"
    return f"system:{ledger or 'events'}"


def _lane_label(lane_id: str) -> str:
    if lane_id == "human":
        return "human"
    if lane_id.startswith("system:"):
        return lane_id.split(":", 1)[1]
    return lane_id


def _timeline_messages(events: list[dict[str, Any]], edges: list[dict[str, Any]], process_ids: set[str]) -> list[dict[str, Any]]:
    by_event = {event["event_id"]: event for event in events}
    messages = []
    for edge in edges:
        from_id = str(edge.get("from", ""))
        to_id = str(edge.get("to", ""))
        if from_id not in process_ids or to_id not in process_ids:
            continue
        event = by_event.get(str(edge.get("event_id")))
        event_index = int(event.get("event_index", 0)) if event else 0
        event_id = str(edge.get("event_id", f"{from_id}-{to_id}-{event_index}"))
        messages.append(
            {
                "message_id": f"message-{event_id}-{len(messages)}",
                "kind": edge.get("kind", "message"),
                "event_id": event_id,
                "event_index": event_index,
                "from_lane_id": f"process:{from_id}",
                "to_lane_id": f"process:{to_id}",
                "label": edge.get("kind", "message"),
                "anchor": f"#edge-{event_id}",
            }
        )
    for event in events:
        if event.get("event_type") != "human_comment":
            continue
        targets = _target_process_lanes(event.get("payload", {}).get("target_refs", []), process_ids)
        for target_lane in targets or ["human"]:
            messages.append(
                {
                    "message_id": f"message-{event['event_id']}-{len(messages)}",
                    "kind": "human_comment",
                    "event_id": event["event_id"],
                    "event_index": event.get("event_index", 0),
                    "from_lane_id": "human",
                    "to_lane_id": target_lane,
                    "label": "human_comment",
                    "anchor": f"#event-{event['event_id']}",
                }
            )
    return messages


def _target_process_lanes(target_refs: list[str], process_ids: set[str]) -> list[str]:
    lanes = []
    for ref in target_refs:
        if ref.startswith("#process-"):
            process_id = ref.removeprefix("#process-")
            if process_id in process_ids:
                lanes.append(f"process:{process_id}")
    return lanes


def _timeline_anchors(timeline: dict[str, Any]) -> list[str]:
    anchors = []
    for lane in timeline.get("lanes", []):
        anchors.extend(str(segment.get("anchor", "")) for segment in lane.get("state_segments", []))
    anchors.extend(f"#{message['message_id']}" for message in timeline.get("messages", []))
    return [anchor for anchor in anchors if anchor]


def _unique_anchors(anchors: list[str]) -> list[str]:
    seen = set()
    unique = []
    for anchor in anchors:
        if anchor in seen:
            continue
        seen.add(anchor)
        unique.append(anchor)
    return unique


def _anchors(events: list[dict[str, Any]], processes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[str]:
    anchors = [f"#event-{e['event_id']}" for e in events]
    anchors += [f"#process-{p['process_id']}" for p in processes]
    anchors += [f"#edge-{e['event_id']}" for e in edges]
    anchors += [f"#state-at-{i}" for i, _ in enumerate(events)]
    return anchors


def _brief_observer_messages(events: list[dict[str, Any]]) -> str:
    if not events:
        return "(none)"
    return "\n".join(f"- `{e['event_id']}` {e['event_type']}: {e.get('payload', {}).get('message', '')}" for e in events)


def _event_lanes(events: list[dict[str, Any]]) -> dict[str, list[str]]:
    lanes = {"transition": [], "process": [], "command": [], "artifact": [], "review": [], "human": [], "observer": [], "notification": [], "reporter": []}
    mapping = {
        "transitions": "transition",
        "process-events": "process",
        "commands": "command",
        "artifacts": "artifact",
        "reviews": "review",
        "human": "human",
        "observer-events": "observer",
        "notifications": "notification",
        "reporter-annotations": "reporter",
    }
    for event in events:
        lane = mapping.get(event.get("ledger"))
        if lane:
            lanes[lane].append(event["event_id"])
    return lanes


def _human_comments(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    comments = []
    for event in events:
        if event.get("event_type") == "human_comment":
            payload = event.get("payload", {})
            comments.append(
                {
                    "event_id": event["event_id"],
                    "author": payload.get("author", ""),
                    "classification": payload.get("classification", ""),
                    "target_refs": payload.get("target_refs", []),
                    "body": payload.get("body", ""),
                    "anchor": f"#event-{event['event_id']}",
                }
            )
    return comments


def _observer_interventions(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    interventions = []
    for event in events:
        if event.get("event_type") in {"intervention_requested", "intervention_delivered", "intervention_acknowledged"}:
            payload = event.get("payload", {})
            interventions.append(
                {
                    "event_id": event["event_id"],
                    "observer_process_id": event.get("process_id"),
                    "target_process_id": payload.get("target_process_id", ""),
                    "message": payload.get("message", ""),
                    "delivery_channel": payload.get("delivery_channel", ""),
                    "delivery_result": payload.get("delivery_result", ""),
                    "anchor": f"#event-{event['event_id']}",
                }
            )
    return interventions


def _mechanism_evidence(rdir: Path, events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    rules = {
        "supervisor": {
            "events": {"supervisor_process_started", "supervisor_process_exited", "supervisor_process_terminated"},
            "artifacts": ["artifacts/supervisor/**/*"],
        },
        "notifications": {
            "events": {"notification_sent", "message_sent", "message_delivered", "message_acknowledged"},
            "artifacts": ["artifacts/notifications/**/*"],
        },
        "github_operations": {
            "events": {"github_operation_planned", "github_operation_executed", "github_operation_failed"},
            "artifacts": ["artifacts/github/**/*"],
        },
        "evaluations": {
            "events": {"evaluation_recorded", "evaluation_command_ran"},
            "artifacts": ["artifacts/evaluations/**/*"],
        },
        "promotion": {
            "events": {"promotion_applied", "promotion_blocked", "deposition_recorded"},
            "artifacts": ["artifacts/deposition/**/*"],
        },
        "retention": {
            "events": {"artifact_retained"},
            "artifacts": ["artifacts/retention/**/*"],
        },
        "ledger_recovery": {
            "events": {"ledger_reconciled"},
            "artifacts": ["artifacts/ledger-recovery/**/*"],
        },
        "merge_repair": {
            "events": {"merge_repair_proposed", "merge_repair_applied", "merge_repair_blocked"},
            "artifacts": ["artifacts/merge-repair/**/*"],
        },
        "report_gui": {
            "events": {"report_gui_manifest_written"},
            "artifacts": ["reports/report-gui-manifest.json"],
        },
    }
    evidence: dict[str, dict[str, Any]] = {}
    for name, rule in rules.items():
        matched_events = [
            {
                "event_id": event.get("event_id", ""),
                "event_type": event.get("event_type", ""),
                "ledger": event.get("ledger", ""),
                "process_id": event.get("process_id", ""),
                "anchor": event.get("anchor", ""),
            }
            for event in events
            if event.get("event_type") in rule["events"]
        ]
        artifacts: list[str] = []
        for pattern in rule["artifacts"]:
            for path in sorted(rdir.glob(pattern)):
                if path.is_file():
                    artifacts.append(str(path.relative_to(rdir)))
        evidence[name] = {"events": matched_events, "artifacts": artifacts}
    return evidence
