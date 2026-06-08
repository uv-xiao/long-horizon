from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .io import read_jsonl, read_toml, write_json, write_text
from .paths import boards_dir, processes_dir, reports_dir, run_dir
from .workflow import allowed_next


def generate_report(root: str | Path, goal_id: str, run_id: str) -> dict[str, Any]:
    data = build_report_data(root, goal_id, run_id)
    rdir = reports_dir(root, goal_id, run_id)
    slides = build_slides_data(data)
    write_json(rdir / "report-data.json", data)
    write_json(rdir / "slides-data.json", slides)
    write_text(rdir / "progress.md", render_markdown(data))
    write_text(rdir / "progress.html", render_html(data))
    write_text(rdir / "slides.html", render_slides_html(slides))
    return data


def build_report_data(root: str | Path, goal_id: str, run_id: str) -> dict[str, Any]:
    rdir = run_dir(root, goal_id, run_id)
    board = read_toml(boards_dir(root, goal_id, run_id) / "task.toml")
    flow = read_toml(rdir / "flow.snapshot.toml")
    processes = [_process_node(path, board) for path in sorted(processes_dir(root, goal_id, run_id).glob("*.toml"))]
    events = _unified_events(rdir)
    edges = _communication_edges(events, processes)
    snapshots = [_snapshot_at(events[: idx + 1], processes, board, idx) for idx in range(len(events))]
    data = {
        "goal_id": goal_id,
        "run_id": run_id,
        "current_state": board.get("current_state"),
        "allowed_next": board.get("allowed_next", allowed_next(flow, board.get("current_state", ""))),
        "playback": {"axis": "event_sequence", "count": len(events), "current_index": max(0, len(events) - 1)},
        "processes": processes,
        "events": events,
        "event_lanes": _event_lanes(events),
        "communication_edges": edges,
        "human_comments": _human_comments(events),
        "observer_interventions": _observer_interventions(events),
        "snapshots": snapshots,
        "anchors": _anchors(events, processes, edges),
    }
    return data


def generate_agent_brief(root: str | Path, goal_id: str, run_id: str, process_id: str = "primary") -> Path:
    rdir = run_dir(root, goal_id, run_id)
    board = read_toml(boards_dir(root, goal_id, run_id) / "task.toml")
    process_path = processes_dir(root, goal_id, run_id) / f"{process_id}.toml"
    proc = read_toml(process_path) if process_path.exists() else {"process_id": process_id, "status": "unknown"}
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
Workspace: `{proc.get('workspace_path', '')}`
State root: `{proc.get('state_path', '')}`

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
        f"Current state: `{data['current_state']}`",
        f"Allowed next: {', '.join(data['allowed_next']) or '(none)'}",
        "",
        "## Processes",
    ]
    for proc in data["processes"]:
        lines.append(f"- `{proc['process_id']}` {proc['role']} {proc['status']} at `{proc['workflow_state']}`")
    lines.extend(["", "## Recent Events"])
    for event in recent:
        lines.append(f"- `{event['event_id']}` `{event['event_type']}` from `{event['process_id']}`")
    lines.extend(["", "## Report", "", "Open `progress.html` for playback, event lanes, graph, and inspector. Open `slides.html` for timeline slides."])
    return "\n".join(lines) + "\n"


def render_html(data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>Long-Horizon Progress</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 0; color: #17202a; background: #f7f7f4; }}
header {{ padding: 16px 20px; background: #16324f; color: white; }}
main {{ display: grid; grid-template-columns: 2fr 1fr; gap: 16px; padding: 16px; }}
section {{ background: white; border: 1px solid #d8d8d2; border-radius: 6px; padding: 12px; }}
#graph svg {{ width: 100%; min-height: 300px; }}
.lane {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.event {{ border: 1px solid #c8c8c0; padding: 4px 6px; border-radius: 4px; background: #fbfbf8; cursor: pointer; }}
.node {{ fill: #fdfdfb; stroke: #365f7d; stroke-width: 1.5; }}
.edge {{ stroke: #8b6f47; stroke-width: 1.5; marker-end: url(#arrow); }}
.marker {{ fill: #c2410c; }}
pre {{ white-space: pre-wrap; }}
</style>
<header><h1>Long-Horizon Progress</h1><div>Goal {html.escape(data['goal_id'])} / Run {html.escape(data['run_id'])}</div></header>
<main>
  <section>
    <label>Event sequence <input id="slider" type="range" min="0" max="{max(0, len(data['events']) - 1)}" value="{max(0, len(data['events']) - 1)}"></label>
    <p><a href="slides.html">Open timeline slides</a></p>
    <div id="graph"></div>
    <h2>Event Lanes</h2>
    <div id="lanes" class="lane"></div>
  </section>
  <section>
    <h2>Inspector</h2>
    <pre id="inspector"></pre>
  </section>
</main>
<script id="report-data" type="application/json">{html.escape(payload)}</script>
<script>
const data = JSON.parse(document.getElementById('report-data').textContent);
const slider = document.getElementById('slider');
const graph = document.getElementById('graph');
const lanes = document.getElementById('lanes');
const inspector = document.getElementById('inspector');
function draw(idx) {{
  const snapshot = data.snapshots[idx] || data.snapshots[data.snapshots.length - 1] || {{}};
  const events = data.events.slice(0, idx + 1);
  const nodes = data.processes;
  const width = 760, height = Math.max(280, nodes.length * 90 + 80);
  let svg = `<svg viewBox="0 0 ${{width}} ${{height}}" role="img"><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="#8b6f47"/></marker></defs>`;
  nodes.forEach((n, i) => {{
    const x = 40 + (i % 3) * 230, y = 40 + Math.floor(i / 3) * 110;
    n._x = x; n._y = y;
    svg += `<a id="process-${{n.process_id}}"><rect class="node" x="${{x}}" y="${{y}}" width="190" height="70" rx="6"></rect><text x="${{x+10}}" y="${{y+22}}">${{n.process_id}} (${{n.role}})</text><text x="${{x+10}}" y="${{y+44}}">status: ${{n.status}}</text><text x="${{x+10}}" y="${{y+62}}">state: ${{n.workflow_state}}</text></a>`;
  }});
  data.communication_edges.forEach(e => {{
    const from = nodes.find(n => n.process_id === e.from), to = nodes.find(n => n.process_id === e.to);
    if (from && to && events.find(ev => ev.event_id === e.event_id)) {{
      svg += `<a id="edge-${{e.event_id}}"><line class="edge" x1="${{from._x+190}}" y1="${{from._y+35}}" x2="${{to._x}}" y2="${{to._y+35}}"></line><circle class="marker" cx="${{(from._x+to._x+190)/2}}" cy="${{(from._y+to._y+70)/2}}" r="4"></circle></a>`;
    }}
  }});
  svg += `</svg>`;
  graph.innerHTML = svg;
  lanes.innerHTML = "";
  data.events.forEach((e, i) => {{
    const div = document.createElement('button');
    div.className = 'event';
    div.id = `event-${{e.event_id}}`;
    div.textContent = `${{i}} ${{e.event_type}}`;
    div.onclick = () => inspect(e);
    if (i > idx) div.style.opacity = "0.35";
    lanes.appendChild(div);
  }});
  inspect(data.events[idx] || data);
}}
function inspect(obj) {{ inspector.textContent = JSON.stringify(obj, null, 2); }}
slider.oninput = () => draw(Number(slider.value));
draw(Number(slider.value));
</script>
</html>
"""


def build_slides_data(data: dict[str, Any]) -> dict[str, Any]:
    slides = []
    for idx, snapshot in enumerate(data["snapshots"]):
        event = data["events"][idx] if idx < len(data["events"]) else {}
        slides.append(
            {
                "index": idx,
                "title": f"{idx}: {event.get('event_type', 'initial')}",
                "event": event,
                "snapshot": snapshot,
                "visible_edges": [
                    edge
                    for edge in data["communication_edges"]
                    if edge.get("event_id") in snapshot.get("visible_event_ids", []) or edge.get("kind") == "spawn"
                ],
                "human_comments": [
                    comment for comment in data["human_comments"] if comment.get("event_id") in snapshot.get("visible_event_ids", [])
                ],
                "observer_interventions": [
                    item for item in data["observer_interventions"] if item.get("event_id") in snapshot.get("visible_event_ids", [])
                ],
            }
        )
    return {
        "goal_id": data["goal_id"],
        "run_id": data["run_id"],
        "timeline": {"axis": data["playback"]["axis"], "count": len(slides)},
        "processes": data["processes"],
        "slides": slides,
    }


def render_slides_html(slides_data: dict[str, Any]) -> str:
    payload = json.dumps(slides_data, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>Long-Horizon Timeline Slides</title>
<style>
body {{ margin: 0; font-family: system-ui, sans-serif; color: #15202b; background: #f6f6f3; }}
header {{ padding: 14px 18px; background: #213547; color: white; display: flex; justify-content: space-between; gap: 16px; align-items: center; }}
main {{ padding: 16px; display: grid; grid-template-columns: 1fr 320px; gap: 16px; }}
.slide {{ background: white; border: 1px solid #d2d2cb; border-radius: 6px; padding: 14px; min-height: 520px; }}
.timeline {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 12px; }}
.timeline button {{ border: 1px solid #b8b8b0; background: #fbfbf9; border-radius: 4px; padding: 4px 7px; cursor: pointer; }}
.timeline button.active {{ background: #2f6f73; color: white; }}
.process-map svg {{ width: 100%; min-height: 330px; }}
.node {{ fill: #fdfdfb; stroke: #315f72; stroke-width: 1.5; }}
.edge {{ stroke: #9a6b38; stroke-width: 1.5; marker-end: url(#arrow); }}
aside {{ background: white; border: 1px solid #d2d2cb; border-radius: 6px; padding: 12px; }}
pre {{ white-space: pre-wrap; font-size: 12px; }}
</style>
<header><h1>Timeline Slides</h1><div>Goal {html.escape(slides_data['goal_id'])} / Run {html.escape(slides_data['run_id'])}</div></header>
<main>
  <section class="slide" id="slide"></section>
  <aside>
    <h2>Inspector</h2>
    <pre id="inspector"></pre>
  </aside>
</main>
<script id="slides-data" type="application/json">{html.escape(payload)}</script>
<script>
const data = JSON.parse(document.getElementById('slides-data').textContent);
const slideEl = document.getElementById('slide');
const inspector = document.getElementById('inspector');
let index = Math.max(0, data.slides.length - 1);
function processMap(slide) {{
  const nodes = slide.snapshot.processes || [];
  const edges = slide.visible_edges || [];
  let svg = '<svg viewBox="0 0 760 420" role="img"><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="#9a6b38"/></marker></defs>';
  nodes.forEach((n, i) => {{
    n._x = 40 + (i % 3) * 235; n._y = 42 + Math.floor(i / 3) * 112;
    svg += `<rect class="node" x="${{n._x}}" y="${{n._y}}" width="195" height="74" rx="6"></rect>`;
    svg += `<text x="${{n._x + 10}}" y="${{n._y + 24}}">${{n.process_id}} (${{n.role}})</text>`;
    svg += `<text x="${{n._x + 10}}" y="${{n._y + 46}}">status: ${{n.status}}</text>`;
    svg += `<text x="${{n._x + 10}}" y="${{n._y + 64}}">state: ${{n.workflow_state}}</text>`;
  }});
  edges.forEach(e => {{
    const from = nodes.find(n => n.process_id === e.from), to = nodes.find(n => n.process_id === e.to);
    if (from && to) svg += `<line class="edge" x1="${{from._x+195}}" y1="${{from._y+37}}" x2="${{to._x}}" y2="${{to._y+37}}"></line>`;
  }});
  return svg + '</svg>';
}}
function draw(i) {{
  index = i;
  const slide = data.slides[index] || {{event: {{}}, snapshot: {{}}}};
  slideEl.innerHTML = `<article data-slide-index="${{index}}"><h2>${{slide.title}}</h2><p>Workflow state: <strong>${{slide.snapshot.current_state || ''}}</strong></p><div class="process-map">${{processMap(slide)}}</div><h3>Human comments</h3><p>${{slide.human_comments.length}}</p><h3>Observer interventions</h3><p>${{slide.observer_interventions.length}}</p><div class="timeline">${{timeline()}}</div></article>`;
  inspector.textContent = JSON.stringify(slide, null, 2);
  document.querySelectorAll('.timeline button').forEach((button, idx) => button.classList.toggle('active', idx === index));
}}
function timeline() {{
  return data.slides.map((slide, i) => `<button onclick="draw(${{i}})">${{i}}</button>`).join('');
}}
document.addEventListener('keydown', event => {{
  if (event.key === 'ArrowRight') draw(Math.min(data.slides.length - 1, index + 1));
  if (event.key === 'ArrowLeft') draw(Math.max(0, index - 1));
}});
draw(index);
</script>
</html>
"""


def _process_node(path: Path, board: dict[str, Any]) -> dict[str, Any]:
    data = read_toml(path)
    return {
        "process_id": data.get("process_id"),
        "role": data.get("role"),
        "status": data.get("status"),
        "workflow_state": data.get("workflow_state", board.get("current_state")),
        "parent_process_id": data.get("parent_process_id", ""),
        "workspace_path": data.get("workspace_path", ""),
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


def _communication_edges(events: list[dict[str, Any]], processes: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
    return edges


def _snapshot_at(events: list[dict[str, Any]], processes: list[dict[str, Any]], board: dict[str, Any], idx: int) -> dict[str, Any]:
    process_status = {proc["process_id"]: dict(proc) for proc in processes}
    current_state = board.get("current_state")
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
    return {
        "event_index": idx,
        "current_state": current_state,
        "processes": list(process_status.values()),
        "visible_event_ids": [e["event_id"] for e in events],
    }


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
