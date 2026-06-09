# V1 Implementation And Verification Guide

This document explains how the v1 long-horizon runtime implements the design
and how the test suite verifies that the design works as an end-to-end system.
It is written for human reviewers who want to inspect the runtime, the tests,
and the generated artifacts rather than only read a feature checklist.

## Verification Philosophy

The v1 runtime is a file-backed process and workflow substrate. It should prove
that a long task can be installed into a repository, started, observed,
interrupted, resumed, branched into child worktrees, joined, reviewed by a
human, and reported through deterministic artifacts.

The test strategy follows three rules:

1. **Unit tests guard mechanism boundaries.** They check that the small write
   gates reject invalid state and preserve invariants.
2. **System tests prove the substrate shape.** They install into temporary
   repositories, run real CLI/API flows, create real git worktrees, write real
   ledgers, and inspect generated reports.
3. **Reports are validated as projections.** Tests do not treat report text as
   source of truth. They inspect canonical files first, then verify that
   `report-data.json` and `progress.html` project those sources correctly.
   `slides.html`/`slides-data.json`, when present, are checked only as
   compatibility aliases to the canonical timeline.

Run all tests with:

```bash
python -m unittest discover -s tests
```

Focused system tests:

```bash
python -m unittest tests.test_st_runtime
python -m unittest tests.test_st_humanize_flows
python -m unittest tests.test_st_cli_report_runtime
python -m unittest tests.test_st_report_server_git_github
```

## Artifact Families

Every run has a stable artifact layout under:

```text
.long-horizon/goals/<goal-id>/runs/<run-id>/
```

The tests validate these file families:

| Artifact family | Purpose | Primary writers | Primary validators |
| --- | --- | --- | --- |
| `boards/task.toml` | Workflow board and current state | `transition.py`, `goal.py` | transition unit/system tests |
| `flow.snapshot.toml` | Run-local immutable workflow definition | `goal.py` | Humanize workflow tests |
| `processes/*.toml` | Process, parent/child, workspace, branch, session metadata | `process.py`, `observer.py`, `git_adapter.py` | process, observer, worktree tests |
| `logs/*.jsonl` | Canonical append-only ledgers | `logger.py` and modules using it | unit tests and all system tests |
| `logs/loose.jsonl` | Non-canonical scratch capture | `logger.py` | loose-log unit test |
| `artifacts/` | Durable task evidence and imported child results | tests, child processes, adapters | transition and worktree tests |
| `artifacts/snapshots/*.json` | Worktree state-copy provenance | `git_adapter.py` | real worktree system test |
| `reports/report-data.json` | Deterministic report projection data | `report.py` | report and Humanize tests |
| `reports/progress.html` | Canonical Perfetto-like timeline report | `report.py` | report tests and server test |
| `reports/slides-data.json` | Compatibility metadata pointing to the canonical timeline | `report.py` | report-server/git/GitHub test |
| `reports/slides.html` | Compatibility redirect/link to `progress.html` | `report.py` | report-server/git/GitHub test |
| `reports/agent-brief.md` | Executor resume/attachment brief | `report.py`, `process.py` | recovery tests |
| `inbox/comments/*.json` | Pushed human/external comment envelopes | `report_server.py`, adapters, tests | comment tests |

## Installation And Repository Layout

### Design Intent

Installation should add the long-horizon runtime without pretending the target
repo is empty. Agent-facing instructions live in `.agents/`; runtime state lives
in `.long-horizon/`.

### Implementation

- `long_horizon/install.py`
  - `install(target, apply=False)` writes an install plan only.
  - `install(target, apply=True)` creates agent-facing rules/skills, runtime
    directories, default config, config catalog, default flow, agent capability
    note, and install ledger entry.
  - `_merge_agents` extends `AGENTS.md`.
  - `_merge_gitignore` ignores runtime state by default.

### Test Design

- `RuntimeSystemTests.create_installed_run` verifies dry-run and applied install.
- `CliReportSystemTest.test_cli_driven_agent_mimic_generates_complete_playback_report`
  verifies the same path through `python -m long_horizon`.
- `ReportServerGitGithubSystemTests.make_git_run` installs into a real temporary
  git repository and commits the installed tracked files before spawning
  worktrees.

### Files Opened For Validation

The tests assert that these files exist or are populated:

- `.agents/rules/long-horizon.md`
- `.long-horizon/config.toml`
- `.long-horizon/flows/default.toml`
- `.long-horizon/logs/install.jsonl`
- target `AGENTS.md`
- target `.gitignore`

### Why This Works

The installer separates the public agent interface from runtime state before
any goal is created. Later tests depend on that separation: the report server,
worktree adapter, process metadata, and comment inbox all operate under the
runtime tree, while agents discover commands through `.agents/`.

## Configuration

### Design Intent

Defaults should be explicit, editable, and validated. A target repo can adjust
workspace mode, reporting, human interaction, sandbox, and adapter policies
without changing runtime code.

### Implementation

- `long_horizon/config.py`
  - writes default `config.toml`;
  - validates configured values;
  - supports `config set` through the CLI.
- `templates/.long-horizon/config-catalog.md`
  - documents configurable defaults and tradeoffs.

### Test Design

- `RuntimeUnitTests.test_config_validation_rejects_invalid_policy`
  attempts to set an invalid workspace policy and expects a `ValueError`.

### Files Opened For Validation

- `.long-horizon/config.toml`
- `.long-horizon/config-catalog.md`

### Why This Works

Config validation is tested before the runtime uses the policy. That keeps
policy drift from silently changing process or workspace semantics.

## Goal And Run Creation

### Design Intent

A goal is the durable contract. A run is one execution attempt against that
contract. Each run snapshots the goal flow so later goal-level edits cannot
rewrite an in-flight run.

### Implementation

- `long_horizon/goal.py`
  - `create_goal` copies or writes `contract.md`;
  - installs or reuses `flow.toml`;
  - records `policy.snapshot.toml`;
  - `create_run` creates run directories, copies `flow.toml` to
    `flow.snapshot.toml`, initializes boards, observer state, ledgers,
    primary process metadata, `agent-brief.md`, and reports.

### Test Design

- Unit tests create runs through `RuntimeUnitTests.make_run`.
- System tests create installed runs before testing transitions, recovery,
  observer intervention, reports, worktrees, and GitHub adapter behavior.
- Humanize tests replace `flow.snapshot.toml` with fixed workflow definitions
  to prove the runtime follows structured flow state rather than hard-coded
  defaults.

### Files Opened For Validation

- `goals/<goal-id>/contract.md`
- `goals/<goal-id>/flow.toml`
- `goals/<goal-id>/policy.snapshot.toml`
- `runs/<run-id>/flow.snapshot.toml`
- `runs/<run-id>/run.toml`
- `runs/<run-id>/boards/task.toml`
- `runs/<run-id>/observer/*.toml`
- `runs/<run-id>/processes/primary.toml`
- `runs/<run-id>/reports/agent-brief.md`
- `runs/<run-id>/reports/report-data.json`

### Why This Works

Tests mutate `flow.snapshot.toml` directly for scenario-specific workflows and
then assert transitions obey that snapshot. This proves the transition engine is
data-driven and run-local.

## Canonical Logging And Loose Capture

### Design Intent

Canonical events should be append-only, typed, ordered, and hash-chained. Loose
notes should be available for capture but should not move workflow state.

### Implementation

- `long_horizon/logger.py`
  - `LEDGERS` defines canonical ledgers;
  - `append_event` validates payload shape, assigns event ids, sequence ids,
    timestamps, causal/source refs, previous hash, and event hash;
  - `_locked` uses a file lock around append operations;
  - `append_loose` writes non-canonical notes to `loose.jsonl`.

### Test Design

- `test_logger_typed_sequence_and_malformed_payload`
  - appends two typed command events;
  - verifies sequence ids and `prev_hash`;
  - verifies malformed payloads are rejected.
- `test_loose_logs_do_not_drive_transitions`
  - writes a loose note saying a plan exists;
  - tries to transition through an artifact gate;
  - expects the transition to stay blocked.

### Files Opened For Validation

- `logs/commands.jsonl`
- `logs/transitions.jsonl`
- `logs/loose.jsonl`

### Why This Works

The transition engine only reads canonical ledgers and real artifacts. A note in
`loose.jsonl` is visible for later promotion but cannot satisfy gates. That
prevents chatty scratch state from becoming workflow truth.

## Workflow Transitions And Gates

### Design Intent

Workflow boards advance only through the transition tool. Transitions should
block until required artifacts, checks, human approvals, or waits are present.

### Implementation

- `long_horizon/transition.py`
  - reads `flow.snapshot.toml` and `boards/task.toml`;
  - appends `transition_requested`;
  - finds a declared transition;
  - validates artifact, check, human, and wait requirements;
  - appends `transition_blocked` or `transition_applied`;
  - mutates `boards/task.toml` only after validation;
  - regenerates reports after state changes or blocks.

### Test Design

- `test_transition_blocks_and_applies_artifact_check_and_human_gates`
  checks artifact, command-check, and human gates.
- `test_st_install_and_run_happy_path`
  executes a full default workflow to completion.
- Humanize v1 and v2 system tests use custom flow snapshots with human gates,
  wait gates, critique gates, artifact gates, and terminal states.

### Files Opened For Validation

- `flow.snapshot.toml`
- `boards/task.toml`
- `logs/transitions.jsonl`
- `logs/commands.jsonl`
- `logs/human.jsonl`
- required `artifacts/...` files
- `reports/report-data.json`

### Why This Works

The tests assert both negative and positive paths. A missing artifact, check,
human approval, or wait creates a blocked transition event. When the exact
evidence is added to the correct file or ledger, the same transition applies
and board state changes.

## Process Model And Recovery

### Design Intent

A runtime process represents an executor session plus workspace state. It can be
interrupted, resumed by another session, and briefed from durable state.

### Implementation

- `long_horizon/process.py`
  - `create_process` writes process metadata and logs `process_spawned`;
  - `interrupt` marks a process interrupted, logs `agent_session_lost` and
    `process_interrupted`, regenerates `agent-brief.md` and reports;
  - `resume` attaches a new session, logs `agent_session_attached`, and
    regenerates briefing/report artifacts.
- `long_horizon/report.py`
  - `generate_agent_brief` includes recovery context when process status is
    interrupted.

### Test Design

- `test_process_interruption_resume_regenerates_brief`
  verifies the unit-level recovery path.
- `test_st_hard_recovery_case`
  interrupts a process, opens `agent-brief.md`, resumes with a new session, and
  continues workflow progress.

### Files Opened For Validation

- `processes/primary.toml`
- `logs/process-events.jsonl`
- `reports/agent-brief.md`
- `reports/report-data.json`

### Why This Works

The replacement executor does not depend on previous chat memory. The process
record, process-event ledger, and regenerated brief contain the recovery state
needed to continue.

## Observer Processes And Intervention

### Design Intent

Observers should be neighboring processes with explicit observe/steer grants.
They can inject steering as append-only intervention events, but they cannot
mutate task workflow boards directly.

### Implementation

- `long_horizon/observer.py`
  - `create_observer` creates a process with role `observer`, target grants,
    observe channels, steer channels, and observer-only write scope;
  - `record_intervention` appends `intervention_requested` and
    `intervention_delivered`, then regenerates reports.

### Test Design

- `test_observer_intervention_is_append_only_and_does_not_mutate_task_board`
  snapshots `boards/task.toml`, records an intervention, and verifies the board
  is unchanged.
- `test_st_parent_child_observer_comment_report`
  adds an observer targeting a child and verifies report communication edges.
- Humanize v1 and v2 system tests include watchdog/alignment observer steering.

### Files Opened For Validation

- `processes/<observer-id>.toml`
- `logs/observer-events.jsonl`
- `boards/task.toml`
- `reports/report-data.json`
- `reports/progress.html`

### Why This Works

Observer writes are constrained to append-only ledgers and observer process
metadata. The board equality assertion proves intervention cannot advance or
rewrite task workflow state.

## Human Comments And Push-Based Review

### Design Intent

Human comments should be pushed into the runtime, imported immediately, logged
as typed human events, deduplicated, and rendered in reports. They should not be
treated as workflow state unless gates explicitly require them.

### Implementation

- `long_horizon/comments.py`
  - `inbox_dir` returns the comment inbox;
  - `import_comments` reads envelopes, deduplicates by channel/comment id,
    writes long bodies as artifacts, appends `human_comment`, appends
    `comment_imported`, removes imported inbox files, and regenerates reports;
  - `_classify` deterministically marks approvals, change requests, questions,
    or notes.
- `long_horizon/report_server.py`
  - `POST /comments` writes an envelope to the inbox, imports it, and
    regenerates reports.
- `long_horizon/github_adapter.py`
  - normalizes GitHub-style review comments into the same envelope shape.

### Test Design

- `test_comment_import_deduplicates_push_envelopes`
  writes the same envelope twice and expects only one human event.
- `test_report_generate_writes_timeline_and_server_imports_pushed_human_comment`
  posts a comment to the local server and verifies it appears in served report
  data.
- Humanize tests use pushed approval envelopes to satisfy human gates.

### Files Opened For Validation

- `inbox/comments/*.json`
- `logs/human.jsonl`
- `logs/notifications.jsonl`
- `artifacts/human-comments/*.md` for large bodies
- `reports/report-data.json`
- `reports/report-data.json` timeline markers and messages

### Why This Works

The same normalized envelope drives local comments, report-server comments, and
GitHub-adapter comments. That keeps human input independent of the transport
channel.

## Report Projection And Timeline

### Design Intent

Reporter output is for humans. It should make the run inspectable without
becoming source of truth. The report must show process topology, workflow
state, communication, interventions, human comments, and event-time order in one
canonical Perfetto-like timeline.

### Implementation

- `long_horizon/report.py`
  - `build_report_data` reads boards, flow snapshot, processes, and all typed
    ledgers;
  - `_unified_events` creates a deterministic event stream;
  - `_communication_edges` derives spawn, steer, artifact import, and review
    edges;
  - `_snapshot_at` computes state after each event;
  - `_workflow_projection` compiles flow states and transitions into selected
    workflow-state detail data;
  - `_timeline_projection` builds lanes, state segments, event markers, and
    inter-process message links;
  - `_event_lanes`, `_human_comments`, and `_observer_interventions` build
    backward-compatible summary data;
  - `render_html` writes `progress.html` with a Perfetto-like timeline, process
    state bars, event markers, message links, selected-state workflow diagram,
    and inspector;
  - `build_slides_data` and `render_slides_html` produce compatibility metadata
    and a redirect/link back to `progress.html`.

### Test Design

- `test_st_install_and_run_happy_path` verifies baseline report files and
  anchors.
- `test_humanize_v1_two_loops_with_inner_fork_join_and_real_human_observer_report`
  verifies process edges, steering messages, artifact-import messages, human
  comments, observer interventions, timeline lanes, state bars, event markers,
  message links, and selected-state diagram markup.
- `test_humanize_v2_plan_lifecycle_rlcr_alignment_and_methodology_report`
  verifies critique, delta card, methodology report, observer intervention, and
  enough snapshots to prove a multi-phase workflow.
- `test_report_generate_writes_timeline_and_server_imports_pushed_human_comment`
  verifies canonical timeline files, compatibility-only slide files, process
  lanes, spawn links, pushed human comment markers, human-comment links, and
  server-refreshed report data.

### Files Opened For Validation

- `reports/progress.html`
- `reports/progress.md`
- `reports/report-data.json`
- `reports/slides.html`
- `reports/slides-data.json`
- source ledgers under `logs/*.jsonl`
- source process files under `processes/*.toml`
- source board file `boards/task.toml`

### Why This Works

The report is regenerated from canonical state after state-changing operations.
Tests validate both the deterministic JSON projections and the HTML markers
needed for human inspection. Timeline lanes, state bars, event markers, and
message links all derive from the same unified event stream and snapshots, so
human visual inspection and machine-checkable data stay aligned. Compatibility
slide files cannot diverge because they only point back to `progress.html`.

## Local Report Server

### Design Intent

The local server should be a helper view and comment ingestion surface, not a
workflow runtime. It serves latest reports and accepts pushed comments.

### Implementation

- `long_horizon/report_server.py`
  - `ReportServer` wraps a `ThreadingHTTPServer`;
  - `GET /` and `GET /progress.html` regenerate and serve `progress.html`;
  - `GET /report-data.json` regenerates and serves report data;
  - `GET /slides.html` and `GET /slides-data.json` serve compatibility aliases;
  - `POST /comments` writes an inbox envelope, imports it, and regenerates
    reports.
- `long_horizon/cli.py`
  - exposes `python -m long_horizon report serve`.

### Test Design

- `test_report_generate_writes_timeline_and_server_imports_pushed_human_comment`
  starts the server on localhost with an OS-assigned port, fetches
  `progress.html`, posts a comment, and fetches `report-data.json` to confirm
  the comment was imported.

### Files Opened For Validation

- `reports/progress.html`
- `reports/report-data.json`
- `reports/slides.html`
- `reports/slides-data.json`
- `inbox/comments/*.json`
- `logs/human.jsonl`
- `logs/notifications.jsonl`

### Why This Works

The server uses the same report generator and comment importer as the CLI/API.
It does not directly edit boards or ledgers except through the canonical comment
import path.

## Git Worktrees, Copy-On-Write State, Import, And Merge

### Design Intent

Parallel or exploratory child processes need their own repository worktree and
their own copied `.long-horizon/` state. The child can diverge locally. The
parent may inspect, import selected child artifacts, and merge a clean child
branch.

### Implementation

- `long_horizon/git_adapter.py`
  - `spawn_child_worktree` runs real `git worktree add -b`, creates parent-side
    child process metadata, writes a snapshot manifest, copies the full logical
    runtime state into the child worktree, and logs `worktree_state_copied`;
  - `import_child_state` copies selected child run artifacts into parent
    `artifacts/imports/<child-process-id>/` and logs `artifact_imported`;
  - `merge_child_branch` runs real `git merge --no-ff --no-edit`, logs
    `child_branch_merged` on success or `child_branch_merge_failed` on failure.
- `long_horizon/cli.py`
  - exposes `process spawn-child-worktree`, `process import-child`, and
    `process merge-child-branch`.

### Test Design

- `test_real_git_worktree_spawn_copies_long_horizon_state_then_parent_imports_child_artifact`
  creates a real temporary git repo, spawns a real child worktree, writes a
  child-local artifact/event, verifies the parent ledger did not receive the
  child event, imports the child artifact, and verifies parent import evidence.
- `test_parent_can_merge_child_branch_after_worktree_exploration`
  commits a tracked file in the child worktree, merges the child branch into the
  parent, verifies the parent file content, and verifies merge provenance.

### Files Opened For Validation

- parent `processes/<child>.toml`
- child `.long-horizon/goals/<goal-id>/runs/<run-id>/...`
- parent `artifacts/snapshots/<child>.manifest.json`
- child `artifacts/snapshots/<child>.manifest.json`
- child `artifacts/candidates/*.md`
- parent `artifacts/imports/<child>/...`
- parent `logs/artifacts.jsonl`
- child `logs/artifacts.jsonl`
- parent `logs/process-events.jsonl`
- tracked repository file merged from child branch

### Why This Works

The worktree tests use real git commands, not mocked branch metadata. The CoW
test proves state divergence by writing a child event and verifying it is absent
from the parent until explicit import. The merge test proves repository content
can flow back through git while runtime evidence records the merge separately.

## Persistent Calculator Demo

### Design Intent

Temporary system tests prove correctness automatically, but human reviewers also
need a durable run they can open, inspect, and clean up explicitly. The
calculator demo exercises the same process model with a small real task:
produce the shortest passing expression calculator by forking child worktrees
for multiple language candidates and merging the winner.

### Implementation

- `scripts/persistent_calculator_demo.py`
  - creates a persistent parent branch and three persistent child branches;
  - installs the template into the parent worktree;
  - creates a calculator goal/run with a Humanize v1-style inner loop;
  - optionally invokes `codex exec` in each child process worktree;
  - records fixed input/output evaluations for each candidate;
  - imports child artifacts into parent state;
  - selects the shortest passing candidate and merges its branch;
  - writes parent-side git and workflow merge artifacts;
  - generates `progress.html` and JSON report data;
  - provides `status` and `clean` commands for reviewers.
- `docs/persistent-calculator-demo.md`
  - documents the run command, persistent branches, key artifacts, and cleanup.

### Test Design

This is a reviewer-facing scenario rather than a unit test. Run:

```bash
python scripts/persistent_calculator_demo.py run --reset --use-codex
```

The fixed task cases are deterministic:

- `1+2*3` -> `7.0`
- `(8-3)/5` -> `1.0`
- `2**3+4` -> `12.0`
- `-3+10/2` -> `2.0`

The demo is considered valid only if all three child candidates run, the parent
selects one passing candidate, the selected branch merges cleanly, and reports
show the process/workflow timeline with human and observer events.

### Files Opened For Validation

- `../long-horizon-calculator-demo/demo-summary.json`
- `../long-horizon-calculator-demo/parent/.long-horizon/goals/calculator-shortest/runs/run-1/reports/progress.html`
- `../long-horizon-calculator-demo/parent/.long-horizon/goals/calculator-shortest/runs/run-1/reports/report-data.json`
- `../long-horizon-calculator-demo/parent/.long-horizon/goals/calculator-shortest/runs/run-1/artifacts/selection/selected-candidate.json`
- `../long-horizon-calculator-demo/parent/.long-horizon/goals/calculator-shortest/runs/run-1/artifacts/process-merges/`
- `../long-horizon-calculator-demo/parent/.long-horizon/goals/calculator-shortest/runs/run-1/logs/`
- `../long-horizon-calculator-demo/worktrees/candidate-*/.long-horizon/`
- `../long-horizon-calculator-demo/host-artifacts/*-codex-output.md`

### Why This Works

The demo proves the runtime can preserve a real long-horizon execution for
manual review. It uses real git branches/worktrees, real child-local state
copies, real candidate source files, real fixed I/O evaluation, real child
artifact import, and real branch merge. When `--use-codex` is enabled, the
candidate source files are produced through the Codex substrate adapter while
workflow state still advances only through long-horizon transitions.

## GitHub Adapter

### Design Intent

External GitHub integration should use repo-local CLI auth configuration and
should normalize review comments into the same comment-envelope contract used
by local and server-based ingestion.

### Implementation

- `long_horizon/github_adapter.py`
  - detects repo-local GitHub CLI auth;
  - refuses silent fallback to unrelated global auth;
  - runs `gh auth status` before `gh repo view`;
  - writes normalized GitHub comment envelopes to the runtime inbox.
- `long_horizon/cli.py`
  - exposes `python -m long_horizon github repo-info --root <repo>`.

### Test Design

- `test_github_adapter_uses_repo_local_auth_and_normalizes_review_comments`
  creates a normalized GitHub comment envelope, writes it to a target run inbox,
  and runs a real `gh repo view` smoke when repo-local auth is available.

### Files Opened For Validation

- `inbox/comments/github-<comment-id>.json`
- current repository metadata returned by `gh repo view`

### Why This Works

The adapter proves the external path at the boundary that matters for v1:
GitHub comments become the same typed input envelope as all other human
comments, and GitHub CLI calls do not silently use unrelated credentials.

## CLI Surface

### Design Intent

Agents and humans should use one public command surface. Direct module APIs are
available for tests, but real use should work through `python -m long_horizon`.

### Implementation

- `long_horizon/cli.py`
  - install/config/goal/run/validate/log/transition/process/observer/report/
    comments/GitHub subcommands;
  - JSON output for commands that return data.

### Test Design

- `test_cli_driven_agent_mimic_generates_complete_playback_report`
  drives install, goal creation, run creation, blocked transition, artifact
  creation, applied transition, typed logging, review transition, and report
  generation through subprocess CLI calls.

### Files Opened For Validation

- generated run tree under `.long-horizon/goals/<goal-id>/runs/<run-id>/`
- `reports/progress.html`
- `reports/progress.md`
- `reports/report-data.json`

### Why This Works

The subprocess test catches argument wiring, JSON output, module entrypoint
behavior, and file generation in the same path a real agent would use.

## Humanize V1-Style Hard Scenario

### Design Intent

The runtime must handle nested long-loop behavior: a human plan gate, builder
round, reviewer round, inner fork-join exploration, observer steering, child
result import, final human acceptance, and completion.

### Implementation

The implementation is generic. The test provides a custom flow snapshot with
states:

```text
plan_acceptance -> build_round -> review_round
-> fork_join_exploration -> final_audit -> completed
```

The runtime uses the same transition, process, observer, logging, comment, and
report modules as every other workflow.

### Test Design

- `test_humanize_v1_two_loops_with_inner_fork_join_and_real_human_observer_report`
  uses fixed fake-agent outputs:
  - local human approval envelope for plan acceptance;
  - builder summary artifact;
  - reviewer verdict event;
  - two child candidate processes;
  - observer intervention targeting one candidate;
  - one blocked join while the second candidate is unfinished;
  - candidate completion events satisfying waits;
  - selected candidate import event;
  - final human approval envelope;
  - completion transition.

### Files Opened For Validation

- custom `flow.snapshot.toml`
- `artifacts/round-001/builder-summary.md`
- `artifacts/candidates/*.md`
- `logs/reviews.jsonl`
- `logs/commands.jsonl`
- `logs/process-events.jsonl`
- `logs/observer-events.jsonl`
- `logs/human.jsonl`
- `logs/artifacts.jsonl`
- `reports/report-data.json`
- `reports/progress.html`

### Why This Works

The scenario is hard because the parent cannot advance until both forked
candidates complete. The test checks the blocked partial join and the later
successful join, proving the wait gate is doing real coordination work.

## Humanize V2-Style Hard Scenario

### Design Intent

The runtime must represent a plan lifecycle with adversarial critique, human
acceptance, RLCR evidence, full alignment observation, human amendment approval,
methodology deposition, and completion.

### Implementation

The test provides a custom flow snapshot with states:

```text
plan_expansion -> adversarial_plan_critique -> plan_acceptance_gate
-> rlcr_round -> full_alignment_check -> plan_amendment_review
-> methodology_report -> completed
```

Again, the runtime uses the same generic mechanisms rather than Humanize-specific
code.

### Test Design

- `test_humanize_v2_plan_lifecycle_rlcr_alignment_and_methodology_report`
  uses fixed fake-agent outputs:
  - expanded plan artifact;
  - adversarial critique event;
  - check result proving the plan survived critique;
  - human plan approval envelope;
  - delta-card artifact and event;
  - observer intervention for alignment drift;
  - amendment approval envelope;
  - methodology report artifact and event;
  - completion transition.

### Files Opened For Validation

- custom `flow.snapshot.toml`
- `artifacts/plan/expanded-plan.md`
- `artifacts/round-005/delta-card.md`
- `artifacts/methodology/process-report.md`
- `logs/reviews.jsonl`
- `logs/commands.jsonl`
- `logs/observer-events.jsonl`
- `logs/human.jsonl`
- `logs/artifacts.jsonl`
- `reports/report-data.json`

### Why This Works

The test validates plan evolution as state and evidence, not chat memory. The
methodology report is an artifact; observer concerns and human approvals are
typed events; completion requires the declared evidence.

## What Reviewers Should Inspect Manually

The tests use temporary repositories, so their exact paths are intentionally not
stable. To inspect an artifact manually, reproduce a focused test under a
debugger or add a local breakpoint/print in the relevant test. Then open the run
directory and inspect these files:

1. `boards/task.toml`
   - Confirm current workflow state and allowed next transitions.
2. `flow.snapshot.toml`
   - Confirm the run uses the intended flow, not a later goal-level edit.
3. `processes/*.toml`
   - Confirm parent/child/observer roles, worktree paths, session ids, and
     grants.
4. `logs/transitions.jsonl`
   - Confirm requested, blocked, and applied transition records.
5. `logs/process-events.jsonl`
   - Confirm process spawn, interruption, resume, child completion, worktree,
     and branch merge events.
6. `logs/artifacts.jsonl`
   - Confirm child artifact creation and parent artifact import provenance.
7. `logs/observer-events.jsonl`
   - Confirm intervention request/delivery records.
8. `logs/human.jsonl`
   - Confirm imported comments, classifications, and target refs.
9. `logs/notifications.jsonl`
   - Confirm comment import notifications.
10. `artifacts/snapshots/*.json`
    - Confirm copied worktree-state manifest and parent head provenance.
11. `artifacts/imports/`
    - Confirm selected child artifacts imported into parent state.
12. `reports/report-data.json`
    - Confirm timeline lanes, state segments, event markers, message links,
      workflow projection, human comments, observer interventions, and stable
      anchors.
13. `reports/progress.html`
    - Confirm process lanes, workflow state bars, human/observer event markers,
      inter-process message links, selected-state transition diagram, and
      click-to-inspect details are visible.
14. `reports/slides.html`, if generated
    - Confirm it is only a compatibility page pointing to `progress.html`.

## Coverage Boundaries

The current suite intentionally does not claim to solve every future mechanism.
Known remaining gaps are tracked in `STATUS.md` and summarized in
`docs/v1-system-test-coverage.md`:

- artifact retention, eviction, compression, and externalization;
- ledger repair and reconciliation;
- remote execution, benchmark, GPU, and task-specific evaluator adapters;
- git merge conflict remediation, rollback, and retry policy.

These are future mechanisms, not hidden assumptions in the current v1 tests.
