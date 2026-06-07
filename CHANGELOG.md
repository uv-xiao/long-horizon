# Change Log

This file tracks commit/PR-sized changes while the template evolves. It is not a release changelog yet.

## Current Change

- Started the first-version implementation PR with an implementation brief and decision list.
- Resolved the v1 workflow-format decision around enforceable structured state, transition validation, and static HTML/SVG reporting.
- Resolved workflow state ownership: only the transition tool mutates workflow boards.
- Resolved workflow storage boundaries: stable goal contracts own runs, and mutable state is isolated per run.
- Resolved flow mutability: each run snapshots the goal-level flow and validates transitions against the snapshot.
- Resolved artifact immutability: evidence artifacts are append-only, while reports are regenerable derived views.
- Resolved validation strategy: v1 uses custom Python validators for workflow files instead of JSON Schema as the enforcement boundary.
- Resolved runtime choice: v1 uses a small Python CLI module exposed through `python -m long_horizon`.
- Resolved structured file format: v1 uses TOML for editable workflow/config/board state and JSONL for append-only ledgers.
- Resolved TOML authorship: agents may edit goal-level flow TOML, while transition tooling owns run board TOML.
- Resolved Codex `/goal` positioning: it is an execution substrate adapter, not the workflow orchestrator.
- Resolved execution substrate updates: reporters generate `agent-brief.md`; tools do not invoke Codex directly.
- Added a process model that ties agent sessions, tmux sessions, workspaces, git branches/worktrees, runs, lanes, and `.long-horizon/` files together.
- Corrected the process model to use copy-on-write `.long-horizon/` state per process/worktree, with parent-side inspect/merge authority and cross-agent adapter guidance.
- Resolved child spawn snapshot policy: copy full logical `.long-horizon/` state by default for agent learning, exclude only configured unsafe/impractical material, and merge back selected child-produced deltas.
- Resolved rejected child merge policy: parent state imports compact learning/rejection summaries by default, while full failed artifacts stay in child state unless explicitly imported.
- Resolved merge context policy: snapshot comparison is recorded as provenance, while actual gates remain merge results, checks, transition validity, and explicit human-risk gates.
- Resolved configuration policy: implementation defaults remain install/task-time configurable through a complete catalog and helper skills for policy changes.
- Resolved branch policy: branchless child processes are allowed only for read-only research, inspection, reporting, or evaluation; repository-editing children require branches.
- Resolved active-run policy changes: they are side artifacts by default and require workflow transitions only when changing contract, gates, evidence, or topology.
- Resolved child policy propagation: active policy changes do not mutate already-spawned children unless the parent explicitly updates, rebriefs, or respawns them.
- Resolved parent wait gates: v1 uses flow-declared join conditions before parent advancement.
- Resolved wait-gate selectors: v1 supports all children, explicit process ids, and lane role selectors, with optional quorum over selected children.
- Resolved wait-gate completion conditions: v1 supports `completed`, `artifact_present`, `checks_passed`, `cancelled_or_rejected`, and conjunctions of those conditions.
- Resolved cancelled/rejected wait behavior: cancelled or rejected children satisfy waits only when the flow explicitly allows `cancelled_or_rejected`.
- Resolved wait-gate quorum semantics: quorum counts selected children satisfying the declared condition set.
- Closed v1 wait-gate semantics with flow-declared timeout/budget terminal states and parent-side wait evaluation artifacts.
- Added the v1 process status vocabulary used by wait gates and process events.
- Resolved watchdog/meta-progress ownership: v1 uses separate observer boards instead of mixing run-health state into task workflow boards.
- Resolved observer process model: v1 supports both checkpoint observer runs and long-running observer sidecars with explicit observe grants, steer grants, and observer-scoped state writes.
- Resolved observer steering: observers may steer task processes through explicit steer grants, with append-only intervention records as the source of truth.
- Resolved observer intervention reporting: reports show compact intervention markers in the main timeline and a detailed intervention lane/table.
- Corrected observer workspace and brief model: observers usually attach to a task/parent workspace while observing granted targets, and `agent-brief.md` remains one process-filtered schema.
- Refined reporter authority: source-backed timelines stay canonical, while configured reporter-authored timeline analysis may be written for human review.
- Added a detailed v1 runtime implementation specification for `/goal`, covering install layout, CLI surface, data contracts, logging, process recovery, reporter playback, comments, tests, and acceptance criteria.
- Moved the v1 testing and acceptance bar to the top of the implementation specification, emphasizing focused unit tests and hard system tests over shallow helper coverage.
- Implemented the first Python v1 runtime with installer, config validation, goal/run creation, typed and loose logging, transition validation, process interruption/resume, observer interventions, human report generation, pushed comment import, and focused unit/system tests.
- Added initial installable configuration catalog and policy-update skill templates.
- Narrowed the runtime `.long-horizon/` ignore rule so tracked template fixtures under `templates/` can include `.long-horizon/` content.
- Resolved v1 reporting views: one static HTML report embeds SVG workflow projection generated from flow snapshot, boards, and transition history.
- Resolved checkpoint policy: v1 uses transition/report checkpoints internally and configurable git commit rules for tracked repository milestones.
- Resolved default safety boundaries: v1 defaults to flexible local autonomy, with strict gates for secrets/auth and irreversible/high-risk actions.
- Resolved adapter learning: learned adapters may be used immediately, logged as append-only artifacts, and revised as usage exposes problems.
- Added repository maintainer rules for separating public template documentation from private research and review logs.
- Added a repo-local Codex skill for evolving the long-horizon template without leaking ignored local paths into public files.
- Moved the temporary brain-simulated design review out of public documentation.
- Removed raw research acquisition status from the public README.
- Moved repo-local skills under `.agents/` and added GitHub/PR workflow skills plus local `gh` auth rules.
- Added `TODO.md` for future template features, starting with adapter learning during long-horizon runs.
