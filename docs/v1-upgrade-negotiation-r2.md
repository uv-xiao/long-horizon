# V1 Upgrade Negotiation, Revision 2

This document is the second negotiation pass after reviewing
`docs/v1-upgrade-negotiation.md` and the inline answers in `STATUS.md`.

It keeps v1 as the product line. The goal is to make v1 more complete by
turning coarse modes and isolated mechanisms into a small, flexible substrate:
feature settings, workspace/virtual processes, async append-only messages,
dynamic workflow state, and stronger prompt/skill guidance.

## Vocabulary Cleanup

The previous wording used terms like "mode", "policy", and "provenance" too
loosely. Use this clearer vocabulary:

- **Feature setting**: a concrete on/off or enum setting in config, such as
  whether the template uses runtime state, prompt templates, a message ledger,
  GitHub channel integration, or a local supervisor.
- **Profile label**: a human-readable summary derived from feature settings,
  such as "runtime-heavy", "native-agent-heavy", or "mixed". It is not source
  of truth.
- **Responsibility map**: a generated explanation of who owns what: the
  template, the target agent, a channel process, or a workflow task.
- **Decision record**: why the current feature settings were chosen, what inputs
  were inspected, and what can be changed later.

So the upgrade should stop making `runtime-owned`, `native-agent`, and `hybrid`
the primary configuration. They can remain derived labels in reports, but the
source of truth should be feature settings plus responsibility map.

## Answered Questions

### What should template code become if a supervisor is optional?

Answer:

The template should implement a **process substrate**, not an always-on
supervisor by default.

Required code shape:

- process records support both workspace processes and virtual processes;
- messages are append-only and async;
- feature settings decide which substrates are enabled;
- a local supervisor can be implemented as one optional substrate for cases that
  need long-running monitor/actor/critic processes;
- native-agent workflows can ignore the supervisor and still use prompts,
  workflow state, messages, reports, and deposition templates.

Implementation implication:

Do not build a heavy supervisor as the next default runtime. First build the
common interfaces that a supervisor would use:

- process kind and state directory;
- optional workspace binding;
- message ledger;
- spawn/observe/steer/join templates;
- feature settings and responsibility map.

Then a simple local supervisor can be added behind `features.local_supervisor`
when the configuration or workflow needs it.

### Why did task setup generate a goal contract scaffold?

Answer:

That was a usability shortcut, but it blurred phase boundaries.

Better model:

- **Task intake** records the human request, task profile, target-agent
  capability fit, recommended feature settings, and recommended initialization
  prompt.
- **Initialization** creates the goal contract, initial workflow, process/message
  topology, feature overrides, and first execution brief.

Task intake may point to a goal-contract template, but should not pretend the
goal contract already exists.

### Who is the "parent process" in dynamic workflow amendment?

Answer:

"Parent process" was too narrow. The correct concept is **workflow owner
process**.

The workflow owner is the process currently allowed to update the workflow state
for its scope. In a simple run, this is the primary/root process. In a forked
run, each child can maintain a local copy-on-write workflow for its own scope,
and the parent/root process decides whether to adopt child workflow changes.

## Resolved Design Direction

### 1. Essential Feature Settings, Not Broad Feature Buckets

User decision:

- Feature settings can be source of truth if they stay essential and tiny.
- Do not encode things like `observer_processes` as global feature toggles when
  they are really workflow-created process roles.
- Settings exist at both install level and task level.
- Skills should guide feature configuration.

Revision:

Use a compact feature setting set:

```toml
[features]
runtime_state = true
prompt_templates = true
transition_validation = true
message_ledger = true
local_supervisor = false
native_agent_loop = false
report_server = true
github_channel = false
```

Avoid global toggles for workflow-specific roles:

- no `observer_processes` toggle;
- no `actor_processes` toggle;
- no `critic_processes` toggle;
- no `deposition_workflow` toggle.

Those are created by initialization/workflow design as process templates or
tasks.

Recommended default for Codex `/goal`:

```toml
[features]
runtime_state = true
prompt_templates = true
transition_validation = true
message_ledger = true
local_supervisor = false
native_agent_loop = true
report_server = true
github_channel = false
```

Reason: Codex `/goal` owns continuation, while the template owns contracts,
evidence, messages, transitions, and reports.

Remaining question:

Should `transition_validation` always be enabled when `runtime_state` is true,
or can a target repo choose prompt-only state without transition validation?

Your answer:

```text

```

### 2. Workspace Processes And Virtual Processes

User decision:

- Human-agent interaction can be handled through the primary process.
- GitHub and other external systems can be virtual processes.
- Sidecar/external processes may not own a workspace; they need a state/logging
  place instead.

Revision:

Process records should support:

```toml
process_id = "github-pr"
process_kind = "virtual" # workspace | virtual | external | supervised
role = "channel"
state_path = ".long-horizon/goals/<goal>/runs/<run>/processes/github-pr/"
workspace_path = ""
parent_process_id = "primary"
```

Process kinds:

- **workspace**: owns or attaches to a filesystem workspace/worktree.
- **virtual**: no workspace; owns state/logs/messages only.
- **external**: adapter handle to outside service/session.
- **supervised**: real OS process managed by optional local supervisor.

Human comments:

- Human input enters through the primary/root process by default.
- External channel processes such as `github-issue` or `github-pr` can receive
  remote human comments and forward them as messages to primary or target
  processes.

> we should only have two kind of processes: workspace and virtual; while external is merged into virtual and supervised is not needed (this is controlled by the configuration, instead).

### 3. Append-Only Async Message Model

User decision:

- Messages should be append-only.
- Messages should be async for robustness.
- GitHub should be a virtual process/channel.
- Ack semantics are unclear and should not block by default.

Revision:

Add a message ledger:

```json
{
  "message_id": "msg_000001",
  "source_process_id": "github-pr",
  "target_process_id": "primary",
  "message_type": "human_comment",
  "thread_id": "pr-12-review",
  "body": "Please explain the merge choice.",
  "artifact_refs": [],
  "causal_refs": [],
  "delivery_channel": "github_pr_comment",
  "delivery_status": "delivered",
  "ack_requested": false,
  "ack_status": "not_required",
  "created_at": "...",
  "delivered_at": "..."
}
```

Rules:

- Sending a message appends an event.
- Delivery status changes append follow-up events.
- Ack is optional and async.
- Workflow gates can require ack/evidence when a task needs it, but the message
  system itself should not block by default.
- Observer steering, GitHub comments, reporter questions, process-to-process
  notes, actor/critic exchanges, and human comments use the same message model.

Remaining question:

Should message threads have a derived mutable latest-state board for report UI
only, or should reports derive threads directly from append-only messages every
time?

Recommendation:

For v1, derive reports directly from append-only messages. Add a cached thread
view only if performance or UI needs it later.

Your answer:

```text
The message looks too complicated. Why we need threads here? I think we need message FIFO for processes. The message FIFO can be file-based when local_supervisor=false, or be in-memory for supervisors (not sure).
I totally don't understand your proposed message threads and things like "derive reports".
What we need is the message between processes.
```

### 4. Merge Flow Assembly Into Initialization

User decision:

- Flow assembly should be merged into goal contract as a comprehensive
  Initialization step.
- Review/completion/deposition should be workflow tasks, not standalone global
  phases.
- Workflow is dynamic and copy-on-write.
- Fixed `flow.toml` plus snapshot mechanism should be replaced by native dynamic
  workflow.

Revision:

Use these top-level phases:

1. **Task intake**: human request, target-agent/capability analysis,
   recommended feature settings, task profile.
2. **Initialization**: goal contract, initial workflow, process/message
   topology, tests/eval task plan, feature overrides, first execution brief.
3. **Execution**: workflow tasks run; processes send messages, produce
   artifacts, and update local workflow copies.
4. **Workflow tasks**: review, completion audit, deposition, merge repair,
   retention, notification, and other mechanisms are tasks inside the workflow.

Workflow storage direction:

- Replace fixed run-level `flow.snapshot.toml` as the only workflow model.
- Introduce versioned, copy-on-write workflow state:

```text
.long-horizon/goals/<goal-id>/workflow/
  versions/<workflow-version-id>.toml
  current.toml

.long-horizon/goals/<goal-id>/runs/<run-id>/processes/<process-id>/workflow/
  current.toml
  amendments/*.toml
```

Each process can maintain a local workflow copy. Adoption/merge of child
workflow changes is explicit.

Compatibility:

Existing `flow.snapshot.toml` can remain as a v1 compatibility input during
migration, but new design should use workflow versions and process-local
workflow state.

Remaining question:

Should initialization create one root workflow version even for prompt-only
tasks, or only when `features.runtime_state = true`?

Recommendation:

Create a root workflow version whenever `features.runtime_state = true`. For
prompt-only tasks, create Markdown initialization artifacts without structured
workflow state.

Your answer:

```text

The versioned workflow is too complicated. We don't need. We just keep one current workflow as flow.toml for each process.

```

### 5. Dynamic Workflow Adjustment

User decision:

- Dynamic workflow amendment should not require human approval by default.
- Active child processes should adopt amendments only by respawn.
- The amendment actor should not be called "parent process"; use a clearer
  owner concept.

Revision:

Use **workflow owner process** for amendment authority.

Amendment policy:

- Low-risk changes can be applied by the workflow owner process.
- Human approval is configurable and risk-based, not default.
- Changes to active child processes require respawn to adopt the new workflow.
- A process can keep its local workflow if not respawned.

Amendment artifact fields:

- owner process;
- affected workflow version;
- reason;
- diff;
- risk class;
- process impact;
- child adoption plan;
- validation evidence;
- approval evidence if required;
- new workflow version id.

Remaining question:

Which risk classes should require human approval by default, if any?

Recommendation:

Default human approval only for:

- safety/secrets/auth changes;
- destructive git or irreversible external effects;
- acceptance criteria removal or weakening;
- human-gate removal;
- cross-process topology changes involving already-running children, unless the
  affected children are respawned.

Your answer:

```text

```

### 6. Tests And Evals Are Workflow Tasks

User decision:

- Tests/evals should be tasks first.
- Commands to run specific tests/evals can be deposited as skills/adapters.
- Transition tooling should not run tests/evals.
- System tests are optional, configured by LLM decisions.

Revision:

Tests/evals belong in Initialization as task definitions:

```toml
[[tasks]]
task_id = "run-unit-tests"
role = "eval"
required_for = ["review", "completion"]
produces = ["artifacts/evals/unit-tests.json"]
```

Execution processes run test/eval tasks and write artifacts/messages. Transition
validation only checks that required evidence exists and matches declared gate
conditions.

System tests:

- not mandatory for every task;
- recommended for high-risk, cross-module, long-running, or user-facing work;
- selected by the LLM/agent during Initialization and recorded as a workflow
  task.

### 7. Prompt And Skill Quality: Rating/Improvement Skill, Not Rigid Validator

User decision:

- Add a prompt template / skill body rating and improvement skill.
- Do not write a restrictive validator program.
- Skills should include examples.

Revision:

Add installable skills:

- `rate-prompt-template`
- `improve-skill-body`

Rating rubric:

- hard constraints;
- required reads;
- allowed writes;
- sequential steps;
- artifacts produced;
- commands/tools used;
- review gate;
- failure handling;
- completion evidence;
- examples;
- no hidden coding in planning-only prompts.

Tests should not enforce a rigid schema. Instead, tests can verify the rating
skill and examples exist, and hard system tests should use the improved prompts
in realistic flows.

### 8. Remove Slide Compatibility

User decision:

- Remove `slides.html` and `slides-data.json`.
- `progress.html` and `progress.md` should show stepping history.

Revision:

Remove slide aliases from report generation, report server, tests, and docs.
Keep:

- `progress.html`;
- `progress.md`;
- `report-data.json`.

### 9. Notification Interface And GitHub Channel

User decision:

- GitHub issues and PRs both matter.
- GitHub channel should create/comment/close issues and PRs.
- Notification is general inter-process messaging.
- Message implementation needs a standalone detailed discussion.
- Notification channels are processes.

Revision:

Add a channel-process interface:

- `github-issue` virtual process;
- `github-pr` virtual process;
- outbound message -> create/comment/close operation;
- inbound comment/event -> append message;
- delivery event -> message status update;
- no special notification ledger separate from messages.

Scope question:

Should the next implementation include full GitHub mutation commands
create/comment/close for both issues and PRs, or first define the channel
interface plus one concrete operation such as PR comment?

Recommendation:

Implement the interface and at least:

- issue comment;
- PR comment;
- inbound issue/PR comment import.

Defer issue/PR creation and closing if needed, unless you want GitHub channel
work to be a major slice.

Your answer:

```text
don't defer. give it full support.

```

### 10. Deposition Writes Directly To `.agents/skills`, With Careful Maintenance

User decision:

- Promoted skills can be written directly into `.agents/skills` for immediate
  adoption.
- It must not be append-only dumping; the skill directory must be maintained.
- Agent review should happen during deposition tasks.
- Memory/rule/skill promotion should have separate templates.
- Human approval is not required by default.

Revision:

Deposition workflow should produce:

- updated `.agents/skills/<skill>/SKILL.md`, `.agents/rules/*.md`, or memory
  files directly when the agent judges promotion is ready;
- review artifact under `.long-horizon/artifacts/deposition/` with problem,
  solution, scope, validation, counterexamples, rollback, and affected files;
- optional human review only when configured or high-risk.

Add separate templates:

- `promote-skill.md`;
- `promote-rule.md`;
- `promote-memory.md`;
- `promote-adapter.md`.

### 11. Merge-Conflict Workflow

User decision:

- Research external best practices before writing the detailed template.
- Merge repair should produce a proposed patch for review first.
- Child process/worktree is preferred, but parent process repair should be
  allowed.

Revision:

Merge repair workflow:

- runs preferably in a child worktree/process;
- inspects base/head/child branches;
- classifies conflict type;
- preserves parent and child intent;
- produces proposed patch first;
- runs selected test/eval tasks;
- records merge-quality evidence;
- only then applies/merges if accepted.

Implementation note:

Before writing the final merge-conflict template, the implementation run should
search/read strong source material on conflict-resolution best practices and
record a short source-backed design note.

## Revised Upgrade Goal Shape

The next implementation goal should be:

1. Add essential feature settings and derived profile/responsibility map.
2. Replace hard-coded operation-mode source of truth with feature settings.
3. Extend process records for workspace, virtual, external, and supervised
   process kinds.
4. Add append-only async message ledger and unify human comments, observer
   interventions, process messages, and GitHub channel events.
5. Rework task setup into task intake; move goal contract and initial workflow
   into Initialization.
6. Add versioned copy-on-write workflow state and dynamic amendment artifacts.
7. Treat tests/evals as workflow tasks that produce evidence; transition
   validation verifies evidence but does not run tests.
8. Add prompt/skill rating and improvement skills with examples.
9. Remove slide compatibility artifacts.
10. Add generic channel-process interface and GitHub issue/PR comment channel.
11. Add detailed deposition templates for skill/rule/memory/adapter promotion.
12. Add source-backed merge-conflict workflow template and proposed-patch flow.
13. Update README, STATUS, config catalog, skills, prompts, reports, and tests.

## Remaining Decisions Before Final Goal Document

Please answer these remaining questions:

1. Should `transition_validation` always be enabled when `runtime_state` is
   true?
2. Should message threads have a derived mutable latest-state board, or should
   reports derive threads directly from append-only messages for now?
3. Should initialization create a root structured workflow version whenever
   `runtime_state = true`?
4. Which workflow amendment risk classes require human approval by default?
5. For GitHub, should the next implementation include create/comment/close for
   both issues and PRs, or start with issue/PR comments and inbound import?

Your answers:

```text
1. Yes
2. I don't understand why we need message threads.
3. Yes.
4. only very dangerous ones.
5. include all.

```
