# First Version Implementation Brief

This PR starts the first implementation slice for the long-horizon template.

The target is a minimal file-and-skill based system that works with Codex `/goal` without wrapping it in a competing long-running loop.

V1 completion note: `docs/v1-completion-upgrade-goal.md` supersedes the first
slice layout where they differ. Current v1 uses per-process `flow.toml`,
process mailboxes, two process kinds, and no slide report artifacts.

The implementation-ready build contract is [v1-runtime-implementation-spec.md](v1-runtime-implementation-spec.md). Use that file as the concrete guide for package shape, CLI commands, installed layout, data contracts, validators, reporter behavior, comment flow, tests, and acceptance criteria.

## Goal

Create the first usable version of the template that can be installed into an existing repository and can support a long-horizon task through durable contracts, flow files, logs, review prompts, reports, and completion audit.

## Initial Scope

1. Installer and capability negotiation.
2. Goal contract and flow TOML.
3. File-backed workflow state machine with transition and validation commands.
4. Process, workspace, version, and checkpoint policy.
5. Logging substrate.
6. Reviewer prompts plus checkpoint and sidecar observer/watchdog processes.
7. Markdown reports plus a static HTML Perfetto-like timeline visualization.
8. Completion audit.
9. Custom Python validators for structured workflow files and Markdown contracts.

## Non-Goals

- No full H2-style runtime in the first version.
- No hosted dashboard, Feishu integration, or external web app in the first version.
- No nested execution loop that competes with Codex `/goal`.
- No task-specific remote execution, benchmark, GPU, or kernel adapter as a default requirement.

## First Implementation Shape

The first version should prefer plain files and repo-local skills:

```text
templates/
  .long-horizon/
    config.toml
    config-catalog.md
    install-plan.md
    agent-capabilities.md
    goal/
      contract.md
      flow.toml
      runs/
        <run-id>/
          run.toml
          flow.snapshot.toml
          boards/
          observer/
          artifacts/
          processes/
          logs/
          reports/
          transitions.jsonl
          process-events.jsonl

.agents/
  skills/
    install-long-horizon/
    configure-long-horizon/
    update-long-horizon-policy/
    goal-contract/
    assemble-flow/
    manage-process/
    transition-workflow/
    observe-workflow/
    review-critic/
    audit-completion/
    report-progress/
    memory-curator/

long_horizon/
  __main__.py
  cli.py
  validate.py
  transition.py
  process.py
  observe.py
  report.py
  report_server.py
  git_adapter.py
  github_adapter.py
```

The installer should inspect existing target-repo agent files, propose an install plan, and only then write template artifacts.

The installed runtime state directory is `.long-horizon/` and should be gitignored by default. It is the per-process workflow state store: child processes inherit a copied snapshot when spawned, then diverge locally until an explicit parent-side merge or promotion imports selected results.

## Configuration Phase

The first version must treat the policies in this document as defaults, not immutable rules. Installation should include a configuration phase, and goal setup may override installation defaults for one task.

The installer should generate a configuration catalog:

```text
.long-horizon/config-catalog.md
```

The catalog should list every configurable mechanism, the current default, tradeoffs, allowed values, where it is stored, what validation applies, and which skill or command can help change it. At minimum it should cover:

- agent substrate and `/goal` usage;
- process workspace mode: original checkout, worktree, branchless read-only process, or native process adapter;
- branch and worktree naming;
- child spawn snapshot exclusions;
- child merge import policy;
- commit, checkpoint, PR, and merge triggers;
- sandbox, command allowlist, network, remote execution, secrets/auth, and destructive-git boundaries;
- workflow gates and human approval modes;
- review, critic, watchdog, and retry budgets;
- artifact retention, eviction, compression, and externalization;
- logging level, memory deposition, learned adapter usage, and adapter promotion;
- report formats and notification channels;
- evaluator adapters, benchmark/profile environments, and task-specific acceptance evidence.

The template should provide skills for policy changes after installation:

```text
.agents/skills/configure-long-horizon/
.agents/skills/update-long-horizon-policy/
```

These skills should inspect the current config, propose a patch, explain consequences, run validators, and write a decision artifact. Configuration changes that affect an active run should be recorded under that run's artifacts as policy-change evidence.

Active-run policy changes are side artifacts by default. They should regenerate validation and reports, but they do not require a workflow transition unless they change goal constraints, human gates, safety boundaries, acceptance evidence, or branch/process topology.

## Runtime Choice

The first CLI should be a Python module with minimal dependencies. v1 commands should run through `python -m long_horizon`:

```bash
python -m long_horizon validate --goal <goal-id> --run <run-id>
python -m long_horizon transition --goal <goal-id> --run <run-id> --to review_required
python -m long_horizon report generate --goal <goal-id> --run <run-id>
python -m long_horizon report serve --goal <goal-id> --run <run-id>
```

Python is the right first runtime because workflow validation, JSONL ledgers, Markdown checks, file operations, and static HTML timeline generation are all direct and testable in one small module. Shell scripts would become brittle once cross-file validation and reporting grow.

The implementation should prefer the Python standard library. TOML is the canonical editable structured format for v1, read with `tomllib` on modern Python. JSONL is the canonical append-only ledger format.

## Codex `/goal` Positioning

Codex `/goal` is an execution substrate adapter in v1. The long-horizon system owns workflow definition, state, validation, transition, logging, and reporting. Codex `/goal` executes work inside the current workflow state and produces artifacts that the transition tool can validate.

For a workflow step, Codex `/goal` may act as:

1. **Builder**: edit files, run commands, investigate, and implement.
2. **Artifact producer**: write summaries, evaluations, proposed plans, reports, and evidence.
3. **Transition requester**: propose that the run move from one state to another with references to supporting artifacts.
4. **Continuation engine**: preserve task context across long work while staying inside the workflow contract.

Codex `/goal` must not directly mutate workflow boards or decide that the workflow advanced. State advances only when the transition tool validates gates and mutates `runs/<run-id>/boards/*.toml`.

Without Codex `/goal`, the first version still works through a weaker manual adapter: a human or another agent reads the generated brief, performs the work, writes artifacts, and invokes the same validation/transition/report commands. This keeps `/goal` useful but not required.

## Execution Substrate Briefing

The execution substrate receives workflow state through generated artifacts, not through wrapper execution. The long-horizon tool must not invoke Codex `/goal` directly.

The reporter generates:

```text
runs/<run-id>/reports/agent-brief.md
```

Codex `/goal`, a non-goal Codex session, another agent, or a human reads `agent-brief.md` and continues work from there. This avoids creating a second loop that competes with `/goal` while still giving the execution substrate fresh workflow context.

The brief uses one schema. It should not fork into unrelated audience-specific brief types by default. Process-local generation may filter sections by process id, so a task process sees observer findings and steering instructions targeted at that process without receiving unrelated observer noise.

The agent brief should include:

- current workflow state;
- allowed next transitions;
- missing artifacts and checks;
- blockers and human gates;
- last transition event;
- next recommended action;
- artifact paths the execution substrate should read or write.

The brief is a derived report and may be regenerated. It is not the source of truth; task boards, observer boards, artifacts, and transition ledgers are.

## Execution Process Model

The first version should model long-horizon execution as explicit processes. A process is:

```text
execution process = agent session/thread + filesystem workspace + optional tmux session
```

Examples:

- a Codex `/goal` thread running in one git worktree inside one tmux session;
- a normal Codex session running in the target repository checkout;
- a human-operated shell using the generated `agent-brief.md`;
- a parallel candidate worker with its own worktree, branch, tmux session, and optional `/goal` thread.
- an observer sidecar process watching one or more task processes through declared observe grants.

The long-horizon workflow defines the logical process model. Each agent substrate adapter implements that model with the primitives it actually has. tmux, Codex thread state, native agent processes, and git worktrees are operational handles.

### Core entities

- **Goal**: stable intent and workflow contract.
- **Run**: one execution attempt against a goal.
- **Process**: one running execution substrate attached to a workspace.
- **Lane**: a logical branch of work inside a run, usually backed by one process and one worktree.
- **Workspace**: the filesystem path where a process reads and writes repository files.
- **Process state root**: the `.long-horizon/` directory visible to one process.
- **Parent process**: the process that spawned another process and can inspect or merge its child process state.
- **Observer process**: a sidecar process that inspects task processes through observe grants and writes observer state, watchdog artifacts, and meta-progress logs.
- **Target workspace**: the checkout or worktree where the process changes project files and stores its process-local `.long-horizon/` state.

### Run directory shape

```text
.long-horizon/goals/<goal-id>/
  contract.md
  flow.toml
  runs/<run-id>/
    run.toml
    flow.snapshot.toml
    boards/
    observer/
      run-health.toml
      watchdog.toml
      evidence-gaps.toml
    artifacts/
    processes/
      primary.toml
      <process-id>.toml
    logs/
      processes/
        <process-id>.md
    reports/
      progress.md
      progress.html
      agent-brief.md
    transitions.jsonl
    process-events.jsonl
```

`run.toml` records run-level execution context:

```toml
goal_id = "goal-001"
run_id = "run-001"
default_process = "primary"

[git]
base_ref = "origin/main"
base_sha = "abc123"
default_branch = "lh/goal-001/run-001"
default_worktree_path = "../repo-lh-worktrees/goal-001/run-001"

[policy]
workspace_mode = "worktree"
parallel_lanes = "allowed"
branch_policy = "code_changes_require_branch"
commit_policy = "configured"
state_model = "copy_on_write"
child_policy_update = "explicit_push_or_respawn"
parent_wait_policy = "flow_declared"
```

Each process file records one execution substrate:

```toml
process_id = "primary"
lane_id = "main"
role = "builder"
substrate = "codex-goal"
status = "active"
parent_process_id = ""
tmux_session = "lh-goal-001-run-001-primary"
workspace_path = "../repo-lh-worktrees/goal-001/run-001"
state_path = "../repo-lh-worktrees/goal-001/run-001/.long-horizon"
branch = "lh/goal-001/run-001"
base_sha = "abc123"
head_sha = ""
codex_thread = ""
started_at = "2026-06-07T00:00:00Z"
```

An observer process records its target and write boundary:

```toml
process_id = "watchdog-primary"
lane_id = "observer"
role = "observer"
substrate = "codex"
status = "active"
parent_process_id = "primary"
observe_targets = ["primary", "candidate-a", "candidate-b"]
observe_channels = ["state_files", "artifacts", "ledgers", "reports", "process_metadata", "tmux_capture"]
steer_targets = ["primary", "candidate-a"]
steer_channels = ["tmux_input", "agent_thread_message", "brief_update"]
write_scope = "observer_only"
attached_process_id = "primary"
tmux_session = "lh-goal-001-run-001-watchdog-primary"
workspace_path = "../repo-lh-worktrees/goal-001/run-001"
state_path = "../repo-lh-worktrees/goal-001/run-001/.long-horizon"
started_at = "2026-06-07T00:00:00Z"
```

An observer process has its own lifecycle, session, status, grants, and process metadata, but it does not require its own workspace by default. In v1, an observer usually attaches to a task or parent process workspace and state root. It may still observe multiple granted target processes, including processes in other workspaces, as long as the observe grants name the targets and read channels. A dedicated observer workspace is optional for heavy tools, isolation, or multi-workspace monitoring where no single task workspace should be privileged.

The process file is mutable process metadata and may be updated by the long-horizon tool. Process history is append-only in `process-events.jsonl`.

V1 process statuses are `active`, `waiting`, `completed`, `cancelled`, `rejected`, `timed_out`, and `budget_exhausted`. The process manager owns process status changes and records them in `process-events.jsonl`.

### Process privilege model

Process privilege follows a parent-child process tree, similar to an operating-system process model.

The transition tool is still the only writer for the boards and transition events inside one process state root, but process authority controls how processes are created, inspected, and merged.

Default v1 privilege rules:

- A process can request transitions inside its own process-local `.long-horizon/` state root.
- A parent process can create child processes.
- A parent process can inspect child process state, reports, artifacts, git branch, head SHA, dirty state, and tmux/session status.
- A parent process can request cancellation or replacement of a child process through the process manager.
- A parent process can wait for selected children to complete, reach a state, produce artifacts, or satisfy checks before the parent advances.
- A parent process can merge or promote a child process back into the parent lane.
- An observer process can read only its granted targets and channels.
- An observer process writes only observer boards, watchdog artifacts, and observer logs.
- An observer process can steer task processes only through explicitly granted steer targets and input channels.
- A child process cannot mutate parent process state directly.
- A sibling process cannot mutate, cancel, or merge another sibling process.
- Candidate processes can write candidate artifacts for their own lane but cannot promote themselves to main without a parent/root-scoped merge.
- Human/operator actions are treated as root-scoped unless a narrower process id is supplied.

Transition requests identify the calling process and operate on that process state root:

```bash
python -m long_horizon transition \
  --goal <goal-id> \
  --run <run-id> \
  --process <process-id> \
  --to review_required
```

Process management commands identify parent/child relationships explicitly:

```bash
python -m long_horizon process spawn \
  --goal <goal-id> \
  --run <run-id> \
  --parent <process-id> \
  --lane candidate-a

python -m long_horizon process inspect \
  --goal <goal-id> \
  --run <run-id> \
  --process candidate-a

python -m long_horizon process wait \
  --goal <goal-id> \
  --run <run-id> \
  --parent primary \
  --gate candidate-join

python -m long_horizon process merge \
  --goal <goal-id> \
  --run <run-id> \
  --parent primary \
  --child candidate-a
```

This is a cooperative workflow authority model, not a security sandbox. It prevents accidental workflow corruption and makes process ownership auditable.

Active-run policy changes do not automatically mutate already-spawned child processes. Existing children continue under their copied snapshot unless the parent explicitly pushes a policy update into that child, asks it to adopt a new generated brief, or cancels and respawns it. New children inherit the parent's updated policy snapshot.

### Single-process progress

When a run has one workspace path and one Codex `/goal` thread, work stays in the same process. New progress does not create a new run. Progress is represented by:

- new artifacts under `runs/<run-id>/artifacts/`;
- new transition events in `transitions.jsonl`;
- updated tool-owned boards;
- regenerated reports;
- updated process metadata such as `head_sha`, status, or last activity.

The same process can pass through many workflow states. A new run is only created when the goal attempt is intentionally restarted, abandoned, or rerun from a different premise.

### Observer processes

V1 must support two observer execution modes:

- **Checkpoint observer run**: a bounded observer process started at configured checkpoints, transitions, reports, or human-requested audits.
- **Long-running observer sidecar**: an observer process kept alive in tmux beside task processes for high-risk or long-running work.

Both modes use the same observe grants, steer grants, workspace attachment policy, and write boundaries. The difference is lifecycle, not authority.

Observer read channels are explicit:

- structured state files: task boards, observer boards, flow snapshot, run config, process metadata from granted targets;
- append-only ledgers: transitions, process events, commands, reviews, evaluations, watchdog logs;
- artifacts and derived reports;
- git status, branch, head SHA, dirty state, and worktree path;
- tmux pane capture or Codex thread text when the selected adapter supports it.

Captured LLM or terminal text is a signal, not hard evidence. If an observer reads "I finished X" from a transcript, it must verify against files, artifacts, checks, or process metadata before marking the run healthy. Unverified claims become evidence gaps.

Observer write surfaces are:

```text
<attached-state-root>/goals/<goal-id>/runs/<run-id>/observer/run-health.toml
<attached-state-root>/goals/<goal-id>/runs/<run-id>/observer/watchdog.toml
<attached-state-root>/goals/<goal-id>/runs/<run-id>/observer/evidence-gaps.toml
<attached-state-root>/goals/<goal-id>/runs/<run-id>/artifacts/watchdog/
<attached-state-root>/goals/<goal-id>/runs/<run-id>/artifacts/watchdog/interventions/
<attached-state-root>/goals/<goal-id>/runs/<run-id>/logs/watchdog.jsonl
<attached-state-root>/goals/<goal-id>/runs/<run-id>/logs/observer-interventions.jsonl
```

Append-only watchdog and intervention events are the source of truth for observer findings. Observer boards are mutable latest-state summaries derived from those events, recent artifacts, and process metadata.

Observer processes never mutate task boards or advance workflow state. Configured transitions may read observer boards as gate input.

Observer steering is allowed in v1. A steering action may send a message to a task process through granted adapter channels such as tmux input, agent thread message, or a regenerated brief. The observer must write an append-only intervention record before or atomically with delivery. The record should include observer process id, target process id, trigger evidence, message body or message artifact path, delivery channel, delivery result, and expected task-process acknowledgement. If delivery cannot be verified, the observer records an evidence gap.

Example commands:

```bash
python -m long_horizon observe checkpoint \
  --goal <goal-id> \
  --run <run-id> \
  --targets primary,candidate-a

python -m long_horizon observe sidecar \
  --goal <goal-id> \
  --run <run-id> \
  --targets primary,candidate-a \
  --tmux-session lh-goal-001-run-001-watchdog-primary

python -m long_horizon observe steer \
  --goal <goal-id> \
  --run <run-id> \
  --observer watchdog-primary \
  --target candidate-a \
  --message-artifact runs/<run-id>/artifacts/watchdog/interventions/intervention-0001.md
```

### Parallel work and branching

When the workflow branches into parallel work or candidate exploration, v1 should create additional processes in the same run:

```text
runs/<run-id>/processes/
  primary.toml
  candidate-a.toml
  candidate-b.toml
```

Each parallel process should normally get:

- its own git worktree;
- its own branch when it may edit repository files;
- its own tmux session;
- its own Codex thread/session, optionally using `/goal`;
- a lane id recorded in artifacts and reports.

Candidate process branches inherit the same goal contract and `flow.snapshot.toml`. Their artifacts should be separated by lane:

```text
runs/<run-id>/artifacts/candidates/<lane-id>/
```

Promotion is explicit. A candidate lane becoming the main path requires a transition or promotion artifact that records:

- promoted lane id;
- source branch and head SHA;
- target branch or merge strategy;
- evidence used for promotion;
- rejected lane summaries.

### Parent wait gates

Some parent states may require a join before advancement. In v1, parent wait gates must be declared in `flow.toml` and captured in the run's `flow.snapshot.toml`. The transition tool blocks parent advancement until the flow-declared child conditions are satisfied.

Wait gate selectors:

- `all`: all child processes of the parent;
- `process_ids`: explicit child process ids;
- `role`: lane role selector, for example `role = "candidate"`.

Arbitrary child predicates are out of scope for v1.

Wait gate conditions:

- `completed`: the child reached a terminal successful process state;
- `artifact_present`: the required flow-declared artifact exists in the child state;
- `checks_passed`: the required flow-declared checks passed for that child;
- `cancelled_or_rejected`: the child was intentionally closed without promotion;
- `timed_out`: the child exceeded a flow-declared time limit;
- `budget_exhausted`: the child exceeded a flow-declared budget limit.

Conditions may be conjoined, for example `artifact_present + checks_passed`. `cancelled_or_rejected`, `timed_out`, and `budget_exhausted` satisfy a wait gate only when the flow explicitly lists them; otherwise a selected child in one of those states blocks or fails the parent transition.

Quorum applies after child selection. A selected child counts toward quorum only if it satisfies the declared condition set.

Timeout and budget limits are flow-declared only in v1. When a limit is exceeded, the process manager records a terminal child status and writes an append-only process event. The transition tool reads that terminal status during wait evaluation; it does not silently reinterpret overdue work as success.

`process wait` evaluates a flow-declared gate and writes a wait evaluation artifact under the parent run, but it does not advance workflow boards by itself. The transition command re-evaluates the gate before mutating parent boards. Wait evaluation artifacts should record the gate id, selector result, selected child ids, required conditions, quorum target, per-child status, missing artifacts/checks, timeout or budget events, and pass/fail result.

### Git and process interaction

Git tracks repository content changes. The `.long-horizon/` files track workflow state, process state, evidence, and decisions.

Default v1 behavior:

- The root process may start in the original checkout or a dedicated worktree, depending on setup policy.
- A child process normally gets a dedicated git worktree.
- A child process that may edit repository files must get a branch.
- A branchless child process is allowed only for read-only research, inspection, reporting, or evaluation tasks, and `branch_policy = "read_only_branchless"` must be recorded in the process metadata.
- Branch names should be deterministic, for example `lh/<goal-id>/<run-id>` and `lh/<goal-id>/<run-id>/<lane-id>`.
- The run records the pinned `base_sha` before work starts.
- Each transition/report records the process branch, `head_sha`, and dirty state.
- Git commits are governed by setup-time commit rules. v1 should provide defaults, but target repos can configure what becomes a commit.
- Rollback means resetting or replacing the process workspace, not rewriting old artifacts.

If work runs in-place instead of a worktree, `workspace_mode = "in_place"` must be recorded in `run.toml`, and reports should warn that repository edits and that process's `.long-horizon/` state share one checkout.

### `.long-horizon/` copy-on-write process state

The `.long-horizon/` directory is gitignored by default and follows the process model with copy-on-write semantics.

Default behavior:

- When a child process is spawned, the process manager creates a new workspace, usually a git worktree.
- Repository files are provided by git worktree checkout.
- The parent process's full logical `.long-horizon/` state is copied into the child workspace as that child process's starting state.
- Copy exclusions are configured and should be limited to unsafe or impractical material such as secrets/auth material, huge binary artifacts, cache/build output, expired credentials, and explicitly evicted artifacts.
- The spawn operation writes a snapshot manifest recording the parent process id, parent state path, parent head SHA, copied paths, excluded paths, and exclusion reasons.
- The child writes to its local `.long-horizon/` state root.
- The parent process state is not changed by child writes until a merge/promote operation imports selected child results.
- Merge imports are explicit append-only events/artifacts in the parent state.
- Reports should show each process's workspace path, state path, branch, parent process, and child processes.

This mirrors process fork semantics: child processes inherit a snapshot, then diverge locally. The workflow does not pretend all worktrees share one live `.long-horizon/` tree.

The default is intentionally generous because inherited logs and artifacts are part of how an agent learns from prior attempts. The key boundary is not a sparse spawn; it is selective merge. A child may read inherited history, but parent state only imports child-produced deltas and explicit summaries.

### Process merge

Merging a child process has two parts:

- **Git merge/cherry-pick/rebase**: imports repository content changes from the child branch/worktree.
- **Workflow merge**: imports selected child-produced `.long-horizon/` deltas, adapter notes, reports, transition summaries, learned lessons, and process metadata from the child state root into the parent state root.

The workflow merge must create a parent-side merge artifact:

```text
runs/<run-id>/artifacts/process-merges/<child-process-id>-merge.md
```

When a workflow state can promote child work, the run's `flow.snapshot.toml`
should include a merge strategy declaration. A minimal v1 shape is:

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

The merge artifact should record:

- child process id and lane id;
- child branch and head SHA;
- child state path;
- inherited snapshot manifest;
- parent head SHA and workflow state at merge time;
- imported artifacts;
- compact rejection or learning summary for failed/non-promoted work;
- rejected artifacts or invalidated evidence that remain in the child state root;
- inherited artifacts that were intentionally not re-imported;
- git merge strategy and result;
- rationale for promotion or rejection.

By default, failed or rejected child work is summarized into the parent so future processes can learn from it. Full failed artifacts remain in the child state root unless the parent marks them as valuable evidence to import. The parent can inspect child state before merge, but it should not rewrite child `.long-horizon/` files in place.

Merge context comparison is provenance, not a default gate. A child result is not rejected merely because the parent advanced after the child was spawned. The real merge gates are git merge result, required tests/evaluations, workflow transition validity, and explicit human gates for constraints, secrets/auth, or irreversible/high-risk actions. Extra explanation is required only when the merge hits workflow-owned conflicts, changed goal constraints, failed required checks, or other direct evidence that the child result no longer applies.

### Cross-agent compatibility

The template must separate the logical process model from each agent substrate's real capabilities.

Codex today is treated as a thread-like substrate, not a true process manager. For Codex:

- the long-horizon process manager creates the workspace/worktree;
- the process manager creates or records the tmux session;
- the Codex session/thread id is recorded when available;
- `/goal` is used as the execution continuation mechanism inside that workspace;
- generated `agent-brief.md` tells Codex what process it is acting as and which local `.long-horizon/` state root to use;
- Codex follows policy rather than relying on native process isolation.

For a future agent with native process management:

- the adapter should map `process spawn`, `inspect`, `cancel`, and `merge` to native process APIs where available;
- the adapter should still persist process records in `.long-horizon/`;
- native process state can be referenced from process TOML, but `.long-horizon/` remains the portable workflow record.

For a basic manual/human adapter:

- the process is a workspace plus generated brief plus shell/tmux context;
- the human or ordinary agent writes artifacts and invokes the same validation, transition, report, and merge commands.

This lets the same workflow policy run on weak thread-like agents and future process-aware agents without changing the workflow contract.

### tmux role

tmux is an operational supervisor:

- it gives each process a stable shell;
- it makes long-running agent sessions discoverable;
- it allows humans to attach, inspect, and intervene.

tmux is not source of truth. If a tmux session disappears, the process record remains, and recovery should either reconnect to the workspace/thread or create a replacement process with `replaces = "<old-process-id>"`.

### Long-horizon file ownership

- The transition tool owns boards and transition events.
- The process manager owns process metadata and process events.
- The watchdog/critic owns observer boards and meta-progress events.
- Agents own proposed artifacts and learned adapter artifacts.
- The reporter owns derived reports.
- Git owns repository content history.

This separation prevents an agent process from confusing “I made code progress” with “the workflow advanced.” Code progress happens in the workspace; workflow progress happens through validated transitions.

## Resolved Decisions

### Workflow representation

The first version should not be Markdown-only. Markdown remains the human-facing surface, TOML holds editable workflow/config/board state, and JSONL holds append-only ledgers.

- `contract.md`: human-readable goal, constraints, non-goals, and acceptance criteria.
- `flow.toml`: declarative workflow states, transitions, required artifacts, checks, and gates.
- `flow.toml` may also declare `merge_strategies`: named parent-side merge policies that describe candidate selectors, repository strategy, workflow imports, required checks, promotion policy, and rejection policy.
- `runs/<run-id>/flow.snapshot.toml`: immutable copy of the goal flow captured when the run starts.
- `runs/<run-id>/boards/*.toml`: mutable task workflow state for one execution attempt, such as current phase, active step, blockers, and candidate scoreboard.
- `runs/<run-id>/observer/*.toml`: mutable observer state for run health, such as drift score, retry pressure, evidence gaps, watchdog findings, budget pressure, and loop suspicion.
- `runs/<run-id>/artifacts/**/*.md|jsonl|toml`: immutable outputs for one execution attempt, such as reviews, evaluations, round summaries, and final reports.
- `runs/<run-id>/transitions.jsonl`: append-only transition history for one execution attempt.

The v1 mechanism should be inspired by Humanize H2's workflow model but should not require H2 or emit a full H2 cartridge.

Python's standard library can read TOML but does not write it. v1 should generate TOML through templates and a deliberately small constrained writer rather than introducing a TOML dependency immediately.

Agents may author and edit goal-level `flow.toml` during planning because it is a design artifact. Agents must not directly author or edit run board TOML. The transition tool owns all `runs/<run-id>/boards/*.toml` writes. Watchdog and critic tooling owns `runs/<run-id>/observer/*.toml`; task transitions should read observer state as gate input when configured, but should not hide observer findings by mutating them.

### Goal and run boundaries

The first version separates stable goal identity from execution attempts:

```text
.long-horizon/goals/<goal-id>/
  contract.md
  flow.toml
  runs/<run-id>/
    flow.snapshot.toml
    boards/
    observer/
    artifacts/
    logs/
    reports/
    transitions.jsonl
```

The goal-level contract and flow are stable across attempts. Each run snapshots the goal flow at start, and transitions validate against that run snapshot rather than the latest goal-level flow. Run-level boards, observer boards, logs, artifacts, reports, and transition history belong to one execution attempt. This prevents failed or abandoned runs from polluting the stable goal contract while still preserving complete evidence and replayability.

### Artifact immutability

Run artifacts are append-only by default. Agents should not rewrite prior evidence artifacts; corrections are written as new superseding artifacts that reference the original. Reports are derived views and may be regenerated from task boards, observer boards, artifacts, logs, and transition history.

Example:

```text
runs/<run-id>/artifacts/reviews/review-0001.md
runs/<run-id>/artifacts/reviews/review-0002.supersedes-review-0001.md
runs/<run-id>/reports/progress.md
runs/<run-id>/reports/progress.html
```

This keeps completion audits trustworthy while still allowing human-facing reports to stay current.

### Transition and validation tool

v1 should include a minimal deterministic tool for transition and validation. Without a command, agents will only follow the workflow files informally.

Example interface:

```bash
long-horizon validate --goal <goal-id>
long-horizon transition --goal <goal-id> --to review_required
```

The tool should check allowed transitions, required artifacts, required fields, and configured gates before mutating board state.

Only the transition tool may mutate `runs/<run-id>/boards/*.toml`. Agents may write goal-level `flow.toml`, proposed artifacts, summaries, evaluations, and transition requests, but they must not directly edit workflow board state. This keeps state transitions auditable and prevents an agent from marking progress without satisfying configured gates.

### Validation mechanism

The first version should use custom Python validators rather than JSON Schema as the primary enforcement mechanism. Validators should parse the structured workflow files, check cross-file relationships, and return precise actionable errors.

Required v1 validation coverage:

- `flow.toml`: states, transitions, required artifacts, checks, gates, and transition target validity.
- `runs/<run-id>/flow.snapshot.toml`: same as `flow.toml`, plus immutable snapshot checks after run creation.
- `runs/<run-id>/boards/*.toml`: task board shape, current state, active step, blockers, and candidate lanes.
- `runs/<run-id>/observer/*.toml`: observer board shape, run-health status, drift score, retry pressure, evidence gaps, watchdog findings, and budget pressure.
- `runs/<run-id>/logs/watchdog.jsonl` and `runs/<run-id>/logs/observer-interventions.jsonl`: append-only observer event shape, intervention delivery records, chronological ordering, and references to observer artifacts.
- `runs/<run-id>/transitions.jsonl`: append-only transition event shape, chronological ordering, and from/to consistency.
- `contract.md`: required headings, non-empty acceptance criteria, non-goals, constraints, and no unresolved placeholders.
- Artifact references: required artifacts exist before a transition, superseding artifacts point at existing originals, and reports are treated as derived views.

JSON Schema files may be added later as documentation or editor assistance, but they are not the v1 enforcement boundary.

### Reporter visualization

The reporter should generate Markdown plus one canonical static HTML timeline
view. `progress.html` is the human report surface. `slides.html`, if present,
is only a compatibility alias to `progress.html`, not a second diagram system.
This is a reporting adapter, not the workflow runtime.

Required generated files:

```text
runs/<run-id>/reports/progress.md
runs/<run-id>/reports/progress.html
runs/<run-id>/reports/report-data.json
runs/<run-id>/reports/agent-brief.md
```

The static HTML report should include:

- current workflow state and allowed next transitions;
- observer health summary, including drift, evidence gaps, retry pressure, and watchdog alerts;
- a Perfetto-like horizontal event-sequence timeline;
- one lane per task process, observer process, human channel, and system channel;
- process state bars showing workflow state/status over event-index ranges;
- clickable state bars that reveal the workflow state-transition diagram for that selected state;
- event markers on their owning lanes, clickable to unfold payload and provenance details;
- message bars/links between process lanes for spawn, steer, ack, artifact import, merge, review, handoff, policy, and human-comment routing events;
- compact observer intervention and human comment markers in the main timeline;
- dedicated observer intervention lane/table with target process, trigger evidence, message artifact/body, delivery channel, delivery result, and acknowledgement state;
- required vs present artifacts;
- blockers and human gates;
- candidate scoreboard when exploration lanes are enabled.

The event timeline is source-backed and generated from typed state, ledgers, process metadata, and artifact references. The reporter should not rewrite those sources or silently edit canonical event history. However, the reporter is not read-only: when enabled by policy, it may write derived timeline analysis for human review. Examples include inferred causal links, suspicious gaps, risk notes, suggested next checks, reviewer questions, and short narrative summaries. These annotations must be marked as reporter analysis and point back to source events or artifacts when possible.

### Timeline and workflow projection

The timeline should learn from Humanize H2's projection pattern without adopting
H2 as a runtime dependency. H2 separates:

1. workflow declaration;
2. compiled graph;
3. runtime projection with node statuses;
4. rendered view.

v1 should use the same conceptual pipeline:

```text
flow.snapshot.toml + boards/*.toml + observer/*.toml + transitions.jsonl
-> WorkflowGraph
-> WorkflowProjection
-> timeline lanes + selected-state transition diagram inside progress.html
```

Generation steps:

1. Parse `runs/<run-id>/flow.snapshot.toml`.
2. Compile workflow states and transitions into graph nodes and directed edges.
3. Read `runs/<run-id>/boards/*.toml`, `runs/<run-id>/observer/*.toml`, and `transitions.jsonl`.
4. Project each node to one status:
   - `pending`: no transition has reached this state;
   - `running`: current board state equals this node;
   - `completed`: a transition has left this state successfully;
   - `failed`: latest transition into or out of this state failed;
   - `blocked`: current board state is this node and a blocker/human gate is active.
5. Mark allowed next transitions from the current state.
6. Render deterministic state-transition detail for the selected state:
   - workflow states as labeled nodes in declaration order;
   - directed transitions with source/target ids;
   - selected state emphasized;
   - allowed next transitions emphasized;
   - completed path muted or green;
   - failed/blocked states highlighted;
   - loop/back transitions shown as explicit curved or annotated links.

The first renderer can use a simple deterministic layered layout rather than a graph layout dependency:

- order nodes by declaration order from `flow.snapshot.toml`;
- place ordinary forward states left-to-right;
- place terminal states at the right edge;
- draw loops and retry transitions as curved top or bottom paths;
- wrap to a second row only when the graph exceeds the configured width.

The current located state is read only from the tool-owned board state, not inferred from report text. A typical board field should be:

```toml
current_state = "running"
```

The reporter uses that value to highlight the current node and uses the validated transition table to highlight allowed next edges. This mirrors H2's projection idea: the visualization is a projection of workflow state, not another source of truth.

Reporter-authored timeline analysis can be rendered near the timeline, but it
must remain visually and structurally separate from canonical state projection.
If analysis later proves wrong, the correction is written as a new annotation or
superseding report artifact rather than mutating the event ledger.

### Commit and checkpoint policy

Workflow transitions, append-only transition events, artifacts, and regenerated reports are the default internal checkpoints. Git commits are controlled by commit rules selected during setup.

Default commit rules:

- transition events are the internal checkpoint;
- generated reports summarize current checkpoint state;
- commit after install when template files or repo rules are written;
- commit after a coherent implementation slice;
- commit before risky rollback-prone exploration;
- commit before PR handoff;
- candidate lanes may commit candidate evidence points when comparison or rollback needs a stable SHA;
- for non-code research tasks, checkpoint by artifact/report, not by git commit unless public docs changed.

The setup phase should let the user configure stricter or looser commit rules. The tool may recommend a commit in reports or `agent-brief.md`, and it may auto-commit only when the active commit policy explicitly allows that trigger.

### Default safety boundaries

v1 should install a flexible default `team/boundaries.md`. The default stance is trusted local autonomy, not conservative lockdown. Most repository work should be allowed unless the target repo overrides the policy.

Default policy:

- **General repository work**: full access by default for reading, editing, testing, refactoring, and local artifact generation.
- **Secrets/auth**: strict by default. Never print, commit, copy, summarize, or expose tokens, credentials, auth files, private keys, cookies, or local GitHub CLI auth.
- **Destructive git**: require explicit human approval for commands such as hard reset, force push, branch deletion, history rewrite, and broad clean operations.
- **Production/infra/legal/compliance**: require explicit human approval before touching production credentials, deployment targets, billing, legal/compliance files, or external infrastructure state.
- **Network/remote execution**: allowed only when the goal contract or an adapter explicitly configures the target and safety expectations.
- **Dependency changes**: allowed by default when justified in the artifact/report trail; target repos may tighten this.
- **Large deletes or generated-file churn**: allowed only with explanation and validation evidence.

The boundary file should be validator-readable so a target repo can tighten or loosen policy without rewriting skills. The default should preserve autonomy while making secrets/auth and irreversible actions hard gates.

### Adapter learning

When a run needs an adapter that does not exist yet, v1 should allow the execution substrate to learn and use that adapter during the active run. Usage does not need to wait for human review, because the default system stance is trusted local autonomy.

Every learned adapter must be logged for later review:

```text
runs/<run-id>/artifacts/adapters/<adapter-id>-v001.md
runs/<run-id>/artifacts/adapters/<adapter-id>-v002.md
```

The adapter artifact should record:

- why the adapter was needed;
- commands, APIs, hosts, files, or external tools it uses;
- safety assumptions and boundaries;
- validation performed before first use;
- observed failures or limitations;
- replacement/supersession relationship when updated.

Learned adapters may be updated in the same run when real usage reveals problems. Updates are append-only superseding artifacts, not rewrites. The reporter should surface newly learned or revised adapters for late human review in `progress.html`, `progress.md`, and `agent-brief.md`.

After the run, adapter deposition may promote a stable learned adapter into `memory/adapters/` or `.agents/skills/`, but promotion is separate from immediate run-time use.

## Open Decisions To Resolve

No major first-version design decisions remain open in this brief. The next step is to turn the resolved decisions into an implementation plan and issues.

## Proposed First Slice

Start with installer, goal contract, flow TOML, and completion audit. These define the public contract and allow later modules to attach without reworking the structure.

The first slice is useful if a user can:

1. Run an install skill in an existing repository.
2. Review an install plan before files are written.
3. Create a goal contract and flow file.
4. Validate and transition workflow state mechanically.
5. Run a long-horizon task with Codex `/goal` while keeping durable artifacts.
6. Inspect Markdown and static HTML timeline reports.
7. Audit completion against acceptance criteria and non-goals.
