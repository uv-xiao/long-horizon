from __future__ import annotations

from pathlib import Path
from typing import Any

from .capabilities import analyze_target, selected_operation_mode
from .io import ensure_dir, write_text, write_toml
from .paths import lh_root
from .time import now_iso


TASK_PHASES = [
    "target-analysis",
    "install-plan",
    "task-setup",
    "goal-contract",
    "flow-assembly",
    "execution-start",
    "live-operation",
    "completion-and-deposition",
]


def create_task_setup(
    root: str | Path,
    request: str,
    task_id: str | None = None,
    target_agent: str = "auto",
    operation_mode: str | None = None,
) -> dict[str, Any]:
    repo = Path(root).resolve()
    caps = analyze_target(repo, target_agent=target_agent, operation_mode=operation_mode)
    mode = str(caps.get("analysis", {}).get("operation_mode", selected_operation_mode(repo)))
    task_id = task_id or _next_task_id(repo)
    tdir = lh_root(repo) / "tasks" / task_id
    ensure_dir(tdir)
    profile = _classify_request(request)
    data = {
        "task": {
            "task_id": task_id,
            "created_at": now_iso(),
            "target_agent": target_agent,
            "operation_mode": mode,
            "profile": profile,
        },
        "request": {"body": request},
        "phases": {"selected": TASK_PHASES},
    }
    write_toml(tdir / "setup.toml", data)
    write_text(tdir / "setup.md", _render_setup(task_id, request, mode, profile, caps))
    write_text(tdir / "goal-contract.scaffold.md", _render_goal_contract(request, mode, profile))
    write_text(tdir / "flow-plan.md", _render_flow_plan(mode, profile))
    write_text(tdir / "execution-brief.md", _render_execution_brief(mode, profile))
    return {"task_id": task_id, "task_dir": str(tdir), "operation_mode": mode, "profile": profile}


def _next_task_id(root: Path) -> str:
    base = lh_root(root) / "tasks"
    ensure_dir(base)
    existing = [path.name for path in base.iterdir() if path.is_dir() and path.name.startswith("task-")]
    return f"task-{len(existing) + 1:03d}"


def _classify_request(request: str) -> str:
    text = request.lower()
    if any(word in text for word in ["benchmark", "sota", "kernel", "profile", "performance"]):
        return "benchmark-loop"
    if any(word in text for word in ["explore", "research", "investigate", "unknown", "candidate"]):
        return "open-exploration"
    if any(word in text for word in ["review", "audit", "inspect"]):
        return "review-only"
    if any(word in text for word in ["bug", "debug", "failure", "regression"]):
        return "debugging"
    return "planned-implementation"


def _render_setup(task_id: str, request: str, mode: str, profile: str, caps: dict[str, Any]) -> str:
    feature_lines = "\n".join(f"- `{key}`: `{value}`" for key, value in sorted(caps.get("features", {}).items()))
    return f"""# Long-Horizon Task Setup

Task: `{task_id}`
Profile: `{profile}`
Operation mode: `{mode}`

## Human Request

{request}

## Selected Phases

{_phase_lines()}

## Capability Evidence

{feature_lines}

## Immediate Next Step

Use the goal-contract template to turn the request into stable objective,
constraints, acceptance criteria, evidence artifacts, evaluator checks, and
human decision points before execution starts.
"""


def _render_goal_contract(request: str, mode: str, profile: str) -> str:
    return f"""# Goal Contract Scaffold

## Objective

{request}

## Context

- Task profile: `{profile}`
- Operation mode: `{mode}`

## Hard Constraints

- Fill in frozen APIs/files, safety boundaries, dependency policy, budget, and
  non-goals.

## Open Search Space

- Fill in candidate dimensions, allowed exploration methods, and when to ask
  the human.

## Acceptance Criteria

- `AC-1`: Define a falsifiable success condition.
- `AC-2`: Define required evidence artifacts.

## Verification

- Correctness checks:
- Evaluation metrics:
- Required artifacts:

## Human Decision Points

- Initial contract approval before execution.
- Review gates for risky plan changes, candidate promotion, and completion.

## Challenge Pass

Before execution, challenge missing acceptance criteria, vague deliverables,
weak evidence, unsafe assumptions, and operation-mode mismatch.
"""


def _render_flow_plan(mode: str, profile: str) -> str:
    return f"""# Goal Flow Plan

Operation mode: `{mode}`
Task profile: `{profile}`

## States

1. `understand`: contract and evidence requirements are clear.
2. `plan`: execution flow and process topology are assembled.
3. `execute`: task processes produce artifacts.
4. `review`: validators, observers, native review, or human gates inspect
   evidence.
5. `complete`: completion audit and deposition are finished.

## Responsibilities

- Runtime-owned mode: use template transition/report/process commands as the
  canonical workflow substrate.
- Native-agent mode: use the target agent's native loop and call template
  validators only at declared gates.
- Hybrid mode: keep native continuation where available, while the template owns
  durable contracts, evidence gates, reports, and workspace state.

## Fork/Join

Declare child processes, candidate lanes, wait gates, quorum, accepted terminal
states, import policy, and merge/eval criteria before spawning children.
"""


def _render_execution_brief(mode: str, profile: str) -> str:
    return f"""# Execution Start Brief

Mode: `{mode}`
Profile: `{profile}`

## Before Starting

- Read `setup.md`, `goal-contract.scaffold.md`, and `flow-plan.md`.
- Confirm the operation mode still matches the target agent's current
  capabilities.
- Run validators or native preflight checks required by the selected mode.

## Execution Rule

Do not let prompts, scripts, or native agent loops mutate workflow state
silently. Every phase decision must leave evidence in `.long-horizon/` or in
the native agent artifact that the operation-mode decision names.
"""


def _phase_lines() -> str:
    return "\n".join(f"- `{phase}`" for phase in TASK_PHASES)
