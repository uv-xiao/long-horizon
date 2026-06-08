# V1 Runtime Implementation Specification

This document is the detailed implementation contract for the first working
version of the long-horizon template runtime. A `/goal` implementation run
should treat this file as the primary build guide, with `README.md` as the
public architecture and `docs/first-version-implementation.md` as the decision
brief.

## Purpose

Build a minimal but real file-backed runtime that can be installed into a
target repository, start a long-horizon task, validate workflow progress, keep
durable logs, recover interrupted agent sessions, and present a human-facing
report.

The runtime must not be a second agent loop competing with Codex `/goal`.
Codex `/goal`, another agent, or a human is an executor attached to a durable
long-horizon process. The long-horizon runtime owns state, validation, logging,
process metadata, reporting, and human interaction routing.

## Testing And Acceptance Bar

Testing is part of the design, not a cleanup step. V1 must prove the template
works as a long-horizon substrate under realistic stress, not merely that helper
functions return expected values.

Do not create many shallow tests for unimportant helpers. Use tests where they
increase confidence in mechanisms that can break long-horizon execution:
installation, configuration, logging integrity, workflow validation, process
recovery, observer intervention, human comments, and report projection.

Use two test classes:

- `ut`: focused unit tests for core mechanism boundaries and validators.
- `st`: hard system tests that exercise the installed template across multiple
  mechanisms in one target repository.

Required unit tests:

- config validation rejects invalid policy values;
- logger appends typed events with per-ledger sequence ids and rejects malformed
  canonical events;
- loose logs cannot directly drive transitions;
- transition validation applies allowed transitions and blocks missing artifact,
  human gate, or wait requirements;
- process interruption/resume updates status and regenerates a targeted agent
  brief;
- observer intervention writes append-only observer events and does not mutate
  task boards;
- comment import deduplicates pushed envelopes and writes typed human events.

Required system tests:

1. **Install-and-run happy path**
   - create a temporary target repo;
   - install `.agents/` and `.long-horizon/`;
   - create a goal/run;
   - log typed and loose events;
   - satisfy an artifact gate;
   - apply transitions to completion;
   - generate `progress.html`, `progress.md`, `report-data.json`,
     `slides.html`, and `slides-data.json`;
   - assert report data contains stable ids, event sequence, process/workflow
     state, anchors, and human-readable report surfaces.
2. **Hard recovery case**
   - create a run with an active process;
   - mark agent session lost/interrupted;
   - regenerate a process-targeted brief;
   - attach a replacement session;
   - continue transition after resume;
   - assert old/new session refs, process events, status changes, and brief
     recovery context are correct.
3. **Parent-child/observer/comment case**
   - represent or spawn child process state;
   - record observer finding/intervention against the child or primary process;
   - import a pushed human comment targeting a stable report anchor;
   - route/comment-log it as a typed human event;
   - generate report;
   - assert graph/report data contains parent-child relation, communication or
     intervention edge, comment event, and no observer mutation of task board.
4. **Report server, real worktree, and external adapter case**
   - serve the latest report over a local helper server;
   - accept a pushed comment envelope through `POST /comments`;
   - spawn a real git child worktree and copy the process-local
     `.long-horizon/` state into it;
   - write child-local artifacts/events without mutating parent state;
   - import selected child artifacts back into parent state with provenance;
   - merge a clean child branch back into the parent checkout with provenance;
   - validate a GitHub adapter path that uses repo-local `gh` auth only.

Acceptance bar:

- The system tests are the real acceptance criteria. A minimal implementation is
  not acceptable unless these tests demonstrate the template works across
  install, workflow, logging, process recovery, observer intervention, reporting,
  and comment import.
- If an implementation problem appears, exploit practical alternatives to make
  the end-to-end mechanism work instead of stopping at scaffolding. Record
  intentionally deferred gaps in `TODO.md`.
- The implementation should also provide a persistent human-review demo for
  realistic inspection when the automated tests use temporary directories. The
  v1 demo is the shortest-expression-calculator workflow documented in
  `docs/persistent-calculator-demo.md`: it runs a Humanize v1-style loop,
  forks at least three child language candidates, imports child evidence,
  selects and merges the shortest passing candidate, and leaves reports,
  ledgers, branches, and worktrees on disk until explicitly cleaned.
- The final verification must report test commands, results, deferred gaps, and
  the commit pushed.

## Source Files

Implementation must align with these public files:

- `README.md`: product architecture and public rationale.
- `docs/first-version-implementation.md`: first-version decision brief.
- `docs/v1-runtime-implementation-spec.md`: implementation contract.
- `templates/.long-horizon/config-catalog.md`: configurable policy catalog.
- `TODO.md`: known future work that should not be overbuilt in v1.
- `.agents/skills/evolve-long-horizon-template/SKILL.md`: maintainer workflow
  for changing this repository.

Public docs must not mention ignored local work paths. Private review logs are
not part of installed template output.

## V1 Scope

V1 must implement this vertical slice:

1. Install agent-facing files into a target repo `.agents/`.
2. Install runtime state/config/templates into target repo `.long-horizon/`.
3. Create a goal and run with a workflow snapshot and boards.
4. Append typed canonical events and loose capture through a logger.
5. Validate and apply workflow transitions from TOML state.
6. Represent processes, child relationships, sessions, interruption, and resume.
7. Generate a process-targeted `agent-brief.md` for executor attachment/resume.
8. Record observer findings and interventions.
9. Generate human-facing `progress.html` and `progress.md`.
10. Import pushed human comment envelopes into typed human events.
11. Provide focused tests for each implemented mechanism.

## V1 Non-Goals

- Do not build a full H2 runtime.
- Do not build a hosted dashboard.
- Do not require Feishu, GitHub webhooks, remote execution, GPUs, or benchmark
  adapters.
- Do not implement artifact eviction beyond a TODO/config placeholder.
- Do not make Markdown timelines a canonical transition source.
- Do not optimize reporter outputs for agent token consumption; reporter is
  human-facing. Agent resumption uses the separate adapter brief.

## Python Package Shape

Prefer Python standard library. Use `tomllib` for reading TOML. For writing TOML,
either implement a tiny deterministic writer for the simple tables v1 needs or
write template strings from typed dictionaries. JSONL is used for append-only
ledgers.

Target package:

```text
long_horizon/
  __init__.py
  __main__.py
  cli.py
  paths.py
  install.py
  config.py
  goal.py
  workflow.py
  validators.py
  logger.py
  transition.py
  process.py
  observer.py
  report.py
  report_server.py
  comments.py
  git_adapter.py
  github_adapter.py
  ids.py
  time.py
  io.py
tests/
  test_install.py
  test_config.py
  test_logger.py
  test_transition.py
  test_process_resume.py
  test_observer.py
  test_report.py
  test_comments.py
```

CLI entrypoint:

```bash
python -m long_horizon <command> ...
```

If packaging metadata is added later, it may expose `long-horizon` as a console
script, but tests and docs should work with `python -m long_horizon`.

## Installed Target Repository Layout

The installer must keep agent affordances and runtime state separate.

Agent-facing installation:

```text
AGENTS.md
.agents/
  rules/
    long-horizon.md
    github-cli.md
  skills/
    configure-long-horizon/
      SKILL.md
    update-long-horizon-policy/
      SKILL.md
    start-long-horizon-task/
      SKILL.md
    resume-long-horizon-process/
      SKILL.md
    inspect-long-horizon-report/
      SKILL.md
    address-long-horizon-comment/
      SKILL.md
  lib/
    long-horizon/
    github/
```

Runtime installation:

```text
.long-horizon/
  config.toml
  config-catalog.md
  install-plan.md
  agent-capabilities.md
  flows/
    default.toml
  inbox/
    comments/
  goals/
  logs/
  artifacts/
  reports/
  memory/
```

Task/run state:

```text
.long-horizon/goals/<goal-id>/
  contract.md
  flow.toml
  policy.snapshot.toml
  runs/<run-id>/
    run.toml
    flow.snapshot.toml
    boards/
      task.toml
    observer/
      run-health.toml
      watchdog.toml
      evidence-gaps.toml
    processes/
      <process-id>.toml
    logs/
      transitions.jsonl
      process-events.jsonl
      commands.jsonl
      artifacts.jsonl
      reviews.jsonl
      human.jsonl
      observer-events.jsonl
      reporter-annotations.jsonl
      notifications.jsonl
      loose.jsonl
      timeline.md
    artifacts/
    reports/
      progress.html
      progress.md
      agent-brief.md
      report-data.json
```

Runtime `.long-horizon/` in target repos is gitignored by default unless a target
repo explicitly chooses to track selected files. Template fixtures in this repo
remain tracked under `templates/`.

## Installer Behavior

Command:

```bash
python -m long_horizon install --target <repo> [--apply]
```

Default behavior without `--apply`:

1. Inspect target repo files: `AGENTS.md`, `CLAUDE.md`, `.agents/`, `.claude/`,
   `.github/`, hooks, scripts, changelog/PR practices, and existing `.gitignore`.
2. Detect available local GitHub CLI/auth support according to the installed
   `.agents/rules/github-cli.md` rule when GitHub integration is requested.
3. Write `.long-horizon/install-plan.md` describing proposed additions, merges,
   and conflicts.
4. Do not modify agent files outside the plan unless `--apply` is passed.

Apply behavior:

1. Create or update `.agents/` rules, skills, and helper docs.
2. Create `.long-horizon/` runtime directories and default config.
3. Merge or append an `AGENTS.md` entrypoint that tells agents where
   long-horizon rules and skills live.
4. Update `.gitignore` to ignore runtime `.long-horizon/` when appropriate.
5. Write an install event to `.long-horizon/logs/install.jsonl`.

Existing user files must not be overwritten without preserving previous content
or producing a conflict/merge artifact.

## Configuration Defaults

Configuration lives in `.long-horizon/config.toml`; the catalog lives in
`.long-horizon/config-catalog.md`.

Defaults that must be represented:

| Policy | Default | Configurable Alternatives |
| --- | --- | --- |
| `agent.substrate` | `codex-goal` | `codex`, `manual`, other adapters |
| `process.workspace_mode` | `worktree` for children | original checkout, read-only branchless, native |
| `process.state_model` | copy full logical `.long-horizon/` into child | exclusions by policy |
| `process.recovery` | interrupted processes are resumable | retry limits, fail-fast |
| `git.commit_policy` | configured meaningful units; no blanket disable | phase, artifact, checks, child merge, human gate |
| `workflow.transition_policy` | Python validators | stricter project-specific validators |
| `workflow.waits` | flow-declared only | selector/quorum/timeout variations |
| `logging.mode` | typed ledgers plus loose capture | stricter or looser capture |
| `logging.hash_chain` | enabled for typed ledgers if implemented | disabled or repair-required |
| `observer.modes` | checkpoint plus sidecar data model | enable/disable per task |
| `observer.workspace_policy` | attach to task/parent workspace | dedicated observer workspace |
| `report.formats` | HTML and Markdown | extra channels/dashboards later |
| `report.timeline_analysis` | disabled or cautious by default | enabled per task |
| `comments.ingestion` | push inbox primary, sync fallback | channel-specific adapters |
| `report.serve` | optional local helper | disabled, polling, SSE later |

Config commands:

```bash
python -m long_horizon config show --root <repo>
python -m long_horizon config validate --root <repo>
python -m long_horizon config set --root <repo> <key> <value>
```

Policy changes during an active run must write a decision artifact under that
run's artifacts and regenerate reports. They require workflow transition only
when changing goal constraints, human gates, safety boundaries, acceptance
evidence, or branch/process topology.

## Goal And Run Creation

Commands:

```bash
python -m long_horizon goal create --root <repo> --goal-id <goal-id> \
  --contract <contract.md>

python -m long_horizon run create --root <repo> --goal-id <goal-id> \
  --run-id <run-id>
```

`goal create`:

- creates `.long-horizon/goals/<goal-id>/contract.md`;
- copies or generates `flow.toml`;
- snapshots current repo policy to `policy.snapshot.toml`;
- logs a goal event.

`run create`:

- creates run directories;
- copies goal flow to `flow.snapshot.toml`;
- creates initial `boards/task.toml`;
- creates initial observer boards;
- creates a primary process record;
- generates `reports/agent-brief.md`, `progress.md`, `progress.html`,
  `report-data.json`, `slides.html`, and `slides-data.json`;
- logs run/process events.

## Workflow Spec

V1 workflow files are TOML. A minimal flow:

```toml
[flow]
id = "default"
initial_state = "understand"
terminal_states = ["completed", "cancelled"]

[[states]]
id = "understand"
kind = "work"

[[states]]
id = "implement"
kind = "work"

[[states]]
id = "review"
kind = "gate"

[[states]]
id = "completed"
kind = "terminal"

[[transitions]]
from = "understand"
to = "implement"
requires_artifacts = ["artifacts/plan.md"]

[[transitions]]
from = "implement"
to = "review"
requires_checks = ["tests_passed"]

[[transitions]]
from = "review"
to = "completed"
requires_human = false
```

Flows that promote child work may include merge strategy declarations:

```toml
[[merge_strategies]]
id = "shortest_passing_candidate"
from_state = "merge_selection"
candidate_processes = ["candidate-a", "candidate-b", "candidate-c"]
selection_metric = "task_defined"
repository_strategy = "merge_child_branch_no_ff"
workflow_imports = ["candidate_summary", "evaluation", "adapter_note", "process_merge_artifact"]
required_checks = ["selected_candidate_tests_passed"]
promotion_policy = "parent_selects_candidate"
rejection_policy = "import compact summaries; leave full failed artifacts in child state"
```

The runtime records repository merge results with `process merge-child-branch`
and records workflow merge decisions in `artifacts/process-merges/`.

Board:

```toml
current_state = "understand"
status = "active"
updated_at = "2026-06-08T00:00:00Z"
allowed_next = ["implement"]
blockers = []
```

Transition command:

```bash
python -m long_horizon transition --root <repo> --goal-id <goal-id> \
  --run-id <run-id> --process-id <process-id> --to <state>
```

Transition validation:

1. Load `flow.snapshot.toml`, not latest goal flow.
2. Load `boards/task.toml`.
3. Confirm requested transition exists from current state.
4. Validate required artifacts/checks/human gates/wait conditions.
5. Write a `transition_requested` event.
6. If blocked, write `transition_blocked` with reasons and leave board unchanged.
7. If valid, append `transition_applied`, update board, regenerate report.

Loose logs must never directly advance state. They may be cited by a typed event
that satisfies a gate.

## Custom Validators

Use custom Python validators as the enforcement boundary. JSON Schema may be
added later for editor help, not for v1 enforcement.

Validators must cover:

- config required sections and allowed values;
- flow states/transitions, unique ids, valid endpoints, reachable initial state;
- board current state exists in snapshot;
- process records include workspace/state/session fields;
- event envelope fields and event-specific payloads;
- artifact refs exist when required;
- human/comment target refs resolve when required;
- report projection references only known ids.

Expose:

```bash
python -m long_horizon validate --root <repo>
python -m long_horizon validate --root <repo> --goal-id <goal-id> --run-id <run-id>
```

## Logger

Logger is the write gatekeeper for append-only records. Agents and reporter may
read files directly, but canonical writes should use logger APIs/commands.

Command:

```bash
python -m long_horizon log append --root <repo> --goal-id <goal-id> \
  --run-id <run-id> --ledger transitions --event-type transition_requested \
  --payload <payload.json>
```

Common event envelope:

```json
{
  "event_id": "evt_000001",
  "event_type": "transition_requested",
  "run_id": "run-001",
  "process_id": "primary",
  "actor": "process:primary",
  "ledger": "transitions",
  "seq": 1,
  "created_at": "2026-06-08T00:00:00Z",
  "observed_at": null,
  "source_refs": [],
  "causal_refs": [],
  "payload": {},
  "prev_hash": null,
  "event_hash": "..."
}
```

Rules:

- Per-ledger `seq` is strict and append-only.
- Cross-ledger ordering is partial; reporter derives display order from causal
  refs, per-ledger seq, and timestamps.
- Use file locks for append operations.
- Read tail, assign next seq, compute hash if enabled, append one JSON line,
  flush/fsync, release lock.
- If lock acquisition fails after retries, write loose capture if possible and
  return a clear failure.
- Typed ledgers can use a lightweight hash chain. If a chain breaks, validators
  fail and repair must be explicit.

Typed ledgers:

- `transitions.jsonl`
- `process-events.jsonl`
- `commands.jsonl`
- `artifacts.jsonl`
- `reviews.jsonl`
- `human.jsonl`
- `observer-events.jsonl`
- `reporter-annotations.jsonl`
- `notifications.jsonl`

Loose capture:

- `loose.jsonl`: default machine-framed loose capture.
- `timeline.md`: mixed human-facing narrative with explicit generated/human/
  reporter sections.
- raw artifacts under `artifacts/raw/` for large outputs.

Loose logs may be promoted only by authorized actors. Promotion creates a typed
event citing the loose record or raw artifact.

Default promotion authority:

- task process: own command/artifact/review events;
- observer: observer findings, evidence gaps, interventions in grant scope;
- parent: child imports, merge decisions, human decisions in parent scope;
- human: explicit decisions and overrides;
- reporter: proposes promotions by default through reporter annotations.

## Process Model

A process is durable state plus a replaceable executor session.

Process record:

```toml
process_id = "primary"
role = "task"
status = "active"
parent_process_id = ""
workspace_path = "/path/to/repo-or-worktree"
state_path = "/path/to/repo-or-worktree/.long-horizon"
branch = "feat/example"
worktree_path = "/path/to/repo-or-worktree"
agent_substrate = "codex-goal"
agent_session_id = "optional-session-or-thread"
tmux_session = "optional-tmux-session"
started_at = "2026-06-08T00:00:00Z"
last_heartbeat_at = "2026-06-08T00:00:00Z"
replaces = ""
```

Statuses:

- `active`
- `waiting`
- `interrupted`
- `resuming`
- `completed`
- `cancelled`
- `rejected`
- `timed_out`
- `budget_exhausted`
- `failed`

Commands:

```bash
python -m long_horizon process create --root <repo> --goal-id <goal-id> \
  --run-id <run-id> --process-id <id> --role task

python -m long_horizon process heartbeat --root <repo> --goal-id <goal-id> \
  --run-id <run-id> --process-id <id>

python -m long_horizon process interrupt --root <repo> --goal-id <goal-id> \
  --run-id <run-id> --process-id <id> --reason <reason>

python -m long_horizon process resume --root <repo> --goal-id <goal-id> \
  --run-id <run-id> --process-id <id> --new-session <session>
```

Interruption/resume:

1. Observer/process manager detects missing heartbeat, dead tmux pane, missing
   agent session, or explicit quit.
2. Logger writes `agent_session_lost` and `process_interrupted`.
3. Process status becomes `interrupted`.
4. Reporter marks process as needing resume.
5. Runtime regenerates process-targeted `agent-brief.md`.
6. New executor attaches to the same workspace/state root.
7. Logger writes `agent_session_attached` with old/new session refs.
8. Process becomes `active` after heartbeat or explicit attach.

The process is failed only after configured recovery retry/budget policy is
exhausted.

## Parent, Child, Worktree, And Git

Child processes that may edit repo files should use branches/worktrees by
default. Branchless children are only for read-only research, inspection,
reporting, or evaluation.

Child spawn:

1. Create branch/worktree when needed.
2. Copy full logical `.long-horizon/` state into child state root, excluding
   unsafe/impractical paths by policy.
3. Write snapshot manifest with copied/excluded paths.
4. Create child process record and `process_spawned` event.
5. Generate child process brief.

Parent authority:

- Parent can inspect child state.
- Parent can wait for child terminal/artifact/check conditions declared in flow.
- Parent can push scoped policy updates, ask child to adopt a regenerated brief,
  or cancel/respawn.
- Parent imports selected child events/artifacts/results through explicit import
  events; child state does not automatically merge.

Git commits are not disabled. Commit triggers are configured by setup/policy and
should create meaningful commit units.

## Wait Gates

V1 wait gates are flow-declared only.

Supported selectors:

- `all`
- explicit process ids
- lane/role selectors

Supported conditions:

- `completed`
- `artifact_present`
- `checks_passed`
- `cancelled_or_rejected`
- `timed_out`
- `budget_exhausted`
- conjunctions of the above

Quorum counts selected children satisfying the declared condition set.
Non-success terminal states count only when explicitly listed. Timeout and
budget limits are terminal statuses recorded by process manager, then read by
transition validation.

## Observer Model

Observer processes are durable processes with observer role. V1 supports both:

- checkpoint observer runs;
- long-running observer sidecars.

Observer defaults:

- observer can attach to a task or parent workspace/state root;
- observer may observe multiple granted target processes, including processes in
  other workspaces;
- dedicated observer workspace is optional for heavy tools or isolation;
- observer writes only observer boards, observer ledgers, watchdog artifacts,
  and intervention records;
- observer cannot mutate task boards or advance workflow state.

Observer process fields:

```toml
process_id = "watchdog-primary"
role = "observer"
status = "active"
attached_process_id = "primary"
observe_targets = ["primary", "candidate-a"]
observe_channels = ["state_files", "artifacts", "ledgers", "reports", "process_metadata", "tmux_capture"]
steer_targets = ["primary"]
steer_channels = ["tmux_input", "agent_thread_message", "brief_update"]
write_scope = "observer_only"
workspace_path = "/path/to/attached/workspace"
state_path = "/path/to/attached/workspace/.long-horizon"
```

Observer events:

- `observer_finding`
- `evidence_gap`
- `intervention_requested`
- `intervention_delivered`
- `intervention_acknowledged`
- `observer_health_update`

Steering:

- requires explicit steer grant;
- happens through adapter channels, not direct task board mutation;
- writes append-only intervention record before or atomically with delivery;
- records delivery result and expected acknowledgement;
- missing delivery/ack evidence becomes an evidence gap.

## Agent Brief

`agent-brief.md` is generated for executor attachment/resume. It belongs to the
agent substrate/resumption mechanism, not the human reporter UX.

Required sections:

- process id, role, workspace path, state path;
- current workflow state and allowed transitions;
- open blockers, human gates, missing artifacts/checks;
- last important events and source refs;
- current process status and recovery context if interrupted;
- observer findings/interventions targeted at this process;
- next recommended action;
- exact commands for validate, transition, log append, report generate;
- rule that workflow boards advance only through transition tool.

The brief uses one schema. Generation may filter by process id so each executor
gets relevant observer findings and steering messages without unrelated noise.

## Reporter

Reporter is human-facing. It generates mutable latest views:

- `reports/progress.html`
- `reports/progress.md`
- `reports/report-data.json`
- `reports/slides.html`
- `reports/slides-data.json`

`agent-brief.md` may be generated by shared code, but it is not part of the
human reporter UX.

The report is a projection, not source of truth. Canonical sources are boards,
typed ledgers, process metadata, and artifacts.

Required HTML features:

- event-sequence slider;
- merged execution graph combining process model and workflow state;
- process nodes showing process id, role, status, current workflow state,
  branch/worktree badge, and risk markers;
- adaptive detail: compact nodes when zoomed out, mini workflow strip at medium
  zoom, expanded workflow details when selected;
- communication edges for durable events: spawn, steer, ack, artifact import,
  merge, policy update, review request/result, handoff;
- observer attachment/grant edges shown separately from noisy read events;
- event lanes by type/severity/process;
- inspector for selected event/process/artifact/annotation;
- compact observer intervention markers in the main timeline;
- dedicated intervention lane/table;
- stable anchors for visible entities.

Slider semantics:

- primary axis is unified event sequence, not wall-clock time;
- slider position N renders state after applying event N;
- inspector can show before/after diff for selected event;
- wall-clock is displayed and filterable, but not correctness ordering.

Report-data pipeline:

```text
split ledgers + boards + process metadata + artifact refs
-> unified event stream
-> projection snapshots by event index
-> report-data.json
-> progress.html playback UI
```

For huge runs:

- embed summaries and source refs, not large raw outputs;
- link large outputs/traces/screenshots as artifacts;
- collapse completed child subtrees;
- filter lanes by type/process/severity;
- sample or window dense markers.

Markdown report:

- keep `progress.md` required as human-readable companion/fallback;
- it does not need to duplicate interactive playback;
- it should summarize current state, blockers, recent events, observer
  interventions, human gates, and report link/path.

Reporter analysis:

- optional/configured;
- stored as `reporter-annotations.jsonl`;
- rendered in timeline/report as clearly marked analysis;
- may include summaries, causal guesses, risks, suggested checks, and questions;
- does not rewrite canonical event history.

## Human Comments And Notifications

Push-based comment ingestion is primary. Pull/sync is a repair fallback.

Inbox:

```text
.long-horizon/inbox/comments/
  <channel>-<external-id>.json
```

Envelope:

```json
{
  "channel": "local",
  "external_comment_id": "comment-001",
  "external_thread_id": "thread-001",
  "author": "human",
  "created_at": "2026-06-08T00:00:00Z",
  "target_refs": ["event:evt_000001"],
  "body": "Please inspect this transition.",
  "body_ref": null
}
```

Import command:

```bash
python -m long_horizon comments import --root <repo> --goal-id <goal-id> \
  --run-id <run-id>
```

Import behavior:

1. Read pending envelopes.
2. Deduplicate by channel plus external comment id.
3. Store body as artifact if large.
4. Append `human_comment` event to `human.jsonl`.
5. Classify deterministic obvious cases when possible.
6. Route follow-up as typed event or reporter annotation.

Comments do not become blocking by default. They block only when targeted at an
explicit gate or when configured author/target/policy rules make them blocking.

Stable report anchors:

- `#event-<event-id>`
- `#process-<process-id>`
- `#artifact-<artifact-id>`
- `#annotation-<annotation-id>`
- `#edge-<event-id>`
- `#state-at-<event-index>`

Notifications:

- log requested/sent/failed/acknowledged/comment-imported events in
  `notifications.jsonl`;
- notifications should point to latest report path plus stable focus refs, not
  immutable report versions;
- default triggers include human gate opened, blocking failure, observer
  intervention requiring acknowledgement, high-risk reporter annotation, child
  completion needing merge decision, budget/time threshold, and final report.

Local report server:

```bash
python -m long_horizon report serve --root <repo> --goal-id <goal-id> \
  --run-id <run-id> [--port 0]
```

V1 server behavior:

- serve latest `progress.html`, `report-data.json`, `slides.html`, and
  `slides-data.json`;
- accept `POST /comments`;
- write normalized envelopes to inbox;
- support polling-first live updates;
- bind localhost by default;
- do not mutate workflow state directly.

## Report Generation Command

```bash
python -m long_horizon report generate --root <repo> --goal-id <goal-id> \
  --run-id <run-id>
```

Report generation should be event-triggered where commands mutate state, and
manual command should remain available. Regeneration may overwrite latest report
files.

The generated HTML should be static/local-first and must not require external
assets. Inline CSS/JS is acceptable for v1.

## Artifact Model

Evidence artifacts are append-only by default. Corrections are written as new
superseding artifacts referencing originals. Reports and boards are mutable
current views.

Artifact event fields:

- `artifact_id`
- `path`
- `kind`
- `created_by`
- `supersedes`
- `source_refs`
- `description`

Large artifact eviction/compression/externalization is a TODO, not required v1.

## Memory And Learned Adapters

V1 should include placeholders/config for learned adapters and memory deposition.
If a missing adapter is learned during a run, it can be used immediately and
logged under run artifacts for human review. Promotion into reusable skills or
memory is future work tracked in `TODO.md`.

## CLI Summary

Required commands:

```bash
python -m long_horizon install --target <repo> [--apply]
python -m long_horizon config show --root <repo>
python -m long_horizon config validate --root <repo>
python -m long_horizon goal create --root <repo> --goal-id <goal-id> --contract <file>
python -m long_horizon run create --root <repo> --goal-id <goal-id> --run-id <run-id>
python -m long_horizon validate --root <repo> [--goal-id <goal-id> --run-id <run-id>]
python -m long_horizon log append --root <repo> --goal-id <goal-id> --run-id <run-id> --ledger <ledger> --event-type <type> --payload <json>
python -m long_horizon transition --root <repo> --goal-id <goal-id> --run-id <run-id> --process-id <process-id> --to <state>
python -m long_horizon process interrupt --root <repo> --goal-id <goal-id> --run-id <run-id> --process-id <process-id> --reason <reason>
python -m long_horizon process resume --root <repo> --goal-id <goal-id> --run-id <run-id> --process-id <process-id> --new-session <session>
python -m long_horizon process spawn-child-worktree --root <repo> --goal-id <goal-id> --run-id <run-id> --parent-process-id <process-id> --process-id <child-id> --branch <branch> --worktree-path <path>
python -m long_horizon process import-child --root <repo> --goal-id <goal-id> --run-id <run-id> --child-worktree-path <path> --child-process-id <child-id> --artifact-path <run-relative-artifact>
python -m long_horizon process merge-child-branch --root <repo> --goal-id <goal-id> --run-id <run-id> --child-process-id <child-id> --branch <branch>
python -m long_horizon report generate --root <repo> --goal-id <goal-id> --run-id <run-id>
python -m long_horizon report serve --root <repo> --goal-id <goal-id> --run-id <run-id>
python -m long_horizon comments import --root <repo> --goal-id <goal-id> --run-id <run-id>
python -m long_horizon github repo-info --root <repo>
```

## Implementation Order

Implement in this order:

1. Paths, ids, time, JSONL/TOML helpers.
2. Installer with dry-run install plan and apply mode.
3. Config model and validators.
4. Goal/run creation with default flow and board.
5. Logger append with typed envelope, loose capture, and tests.
6. Workflow validator and transition command.
7. Process records and interrupt/resume brief generation.
8. Observer event helpers and intervention records.
9. Report data projection and basic HTML/Markdown generation.
10. Comment inbox import and typed human events.
11. Local report server, real git worktree child spawning/import, and GitHub
    adapter smoke path.
12. Docs, TODO gaps, changelog, final verification.

## Test Requirements

Follow the top-level testing and acceptance bar in this document. Tests should
use temporary directories and `python -m long_horizon` or direct module APIs.
Unit tests should stay focused on important mechanism boundaries. System tests
must validate the template as an installed, end-to-end runtime under realistic
long-horizon cases.

## Acceptance Criteria

The implementation is complete enough when all are true:

1. A target repo can be installed with `.agents/` and `.long-horizon/`.
2. A goal/run can be created from a contract.
3. Typed events append through logger with sequence ids.
4. Loose capture exists and cannot directly drive transitions.
5. A workflow transition can be validated/applied or blocked with reasons.
6. A process can be marked interrupted and resumed through a regenerated brief.
7. Observer findings/interventions are represented as append-only events.
8. `progress.html` shows a human-readable execution projection with event
   slider data, process/workflow state, event lanes, and inspector data.
9. `progress.md` summarizes the same run for human reading.
10. A pushed comment envelope can be imported as a typed human event.
11. Clean child branch merges produce both git provenance and a parent-side
    workflow merge artifact under `artifacts/process-merges/`.
12. The persistent calculator demo can be run for human inspection, including
    Codex-backed child candidate generation when `--use-codex` is enabled.
13. Tests pass, or any intentionally deferred item is explicit in `TODO.md`.

## Commit And Documentation Rules

- Keep commits scoped and meaningful.
- Update `CHANGELOG.md` for implementation-sized changes.
- Update public docs only when behavior or usage changes.
- Do not add private reasoning, ignored paths, or run logs to public files.
- Do not stage target-run `.long-horizon/` output, caches, or generated local
  test repos.
