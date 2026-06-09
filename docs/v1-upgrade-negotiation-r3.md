# V1 Upgrade Negotiation, Revision 3

This document is the third negotiation pass after reviewing
`docs/v1-upgrade-negotiation-r2.md` and the latest inline answers.

The main correction in this round is to simplify the runtime model. Revision 2
introduced too many intermediate abstractions: message threads, workflow
versions, and four process kinds. The v1 upgrade should instead keep the model
close to what agents and humans can operate reliably:

- two process kinds: workspace and virtual;
- one FIFO mailbox per process;
- one current `flow.toml` per process;
- copy-on-write by copying process state when a child process is spawned;
- full GitHub issue/PR channel support;
- dangerous actions require human approval by default.

## Decisions Locked By This Round

### 1. Feature Settings Remain The Source Of Truth

Keep small feature settings as the concrete configuration layer.

```toml
[features]
runtime_state = true
prompt_templates = true
transition_validation = true
message_mailboxes = true
local_supervisor = false
native_agent_loop = false
report_server = true
github_channel = false
```

Changes from revision 2:

- rename `message_ledger` to `message_mailboxes`;
- do not model observer, actor, critic, deposition, or retention as global
  feature toggles;
- keep operation/profile names only as derived labels in reports and decision
  records.

Default for Codex `/goal`:

```toml
[features]
runtime_state = true
prompt_templates = true
transition_validation = true
message_mailboxes = true
local_supervisor = false
native_agent_loop = true
report_server = true
github_channel = false
```

Decision: when `runtime_state = true`, `transition_validation` is enabled by
default and should not be disabled for normal runtime-driven workflows. A repo
can still run prompt-only tasks by setting `runtime_state = false`.

Rationale: runtime state without transition validation creates durable files
that look authoritative but do not protect gates. That is a weak default.

### 2. Only Two Process Kinds

Use only:

- **workspace process**: owns or attaches to a repo directory or git worktree.
- **virtual process**: has no workspace; owns state, mailboxes, logs, and
  adapter handles.

Do not keep separate `external` or `supervised` process kinds.

- External systems such as GitHub, a report channel, or a human channel are
  virtual processes with adapter metadata.
- Supervision is a runtime configuration choice, not a process kind.

Process record shape:

```toml
process_id = "github-pr"
process_kind = "virtual" # workspace | virtual
role = "channel"
parent_process_id = "primary"
state_path = ".long-horizon/goals/<goal>/runs/<run>/processes/github-pr/"
workspace_path = ""

[adapter]
type = "github_pr"
repo = "owner/name"
pr_number = 12

[runtime]
managed_by_local_supervisor = false
session_handle = ""
```

For a workspace process:

```toml
process_id = "actor-a"
process_kind = "workspace"
role = "actor"
parent_process_id = "primary"
state_path = ".long-horizon/goals/<goal>/runs/<run>/processes/actor-a/"
workspace_path = "../long-horizon-actor-a"
branch = "lh/<goal>/actor-a"
```

### 3. Process Mailboxes Replace Message Threads

Revision 2's message thread model was too complicated. V1 should implement
process-to-process messaging as FIFO mailboxes.

Each process has:

```text
.long-horizon/goals/<goal>/runs/<run>/processes/<process-id>/mailbox/
  inbox.jsonl
  outbox.jsonl
  ack.jsonl
```

Message envelope:

```json
{
  "message_id": "msg_000001",
  "source_process_id": "github-pr",
  "target_process_id": "primary",
  "message_type": "human_comment",
  "body": "Please explain the merge choice.",
  "artifact_refs": [],
  "causal_refs": [],
  "requires_ack": false,
  "created_at": "2026-06-09T12:00:00Z"
}
```

Rules:

- appending to `outbox.jsonl` records send intent;
- appending to target `inbox.jsonl` records delivery;
- `ack.jsonl` records optional acknowledgement;
- delivery is async;
- FIFO order is per target process inbox;
- if `local_supervisor = false`, mailboxes are file-based;
- if `local_supervisor = true`, a supervisor may keep in-memory queues while
  still flushing durable JSONL records;
- workflow gates can require an ack or response artifact, but the mailbox
  mechanism itself does not block.

Report generation should read process mailboxes and event ledgers directly. It
does not need message threads or a mutable thread board in v1.

### 4. Workflow State Is One `flow.toml` Per Process

Revision 2's versioned workflow store was too heavy.

Use one current workflow file per process:

```text
.long-horizon/goals/<goal>/runs/<run>/processes/<process-id>/flow.toml
.long-horizon/goals/<goal>/runs/<run>/processes/<process-id>/flow-amendments.jsonl
```

Initialization creates the root process `flow.toml` whenever
`runtime_state = true`.

Copy-on-write rule:

- when a child process is spawned, its process directory receives a copy of the
  parent's current `flow.toml`;
- the child may amend its own `flow.toml`;
- the parent does not automatically adopt child changes;
- join/import can inspect the child's `flow.toml`, amendments, artifacts, and
  messages, then decide whether to merge work, respawn children, or amend the
  parent flow.

This preserves the user's expected mental model: `.long-horizon/` state is
copied into child process state, then diverges locally.

### 5. Dynamic Workflow Amendment Uses The Workflow Owner

Use **workflow owner process** as the authority concept. In a simple run this is
the root process. In a forked run, a child owns its own copied `flow.toml`, while
the parent/root decides whether to adopt child results.

Amendment artifact:

```json
{
  "amendment_id": "amend_000001",
  "owner_process_id": "primary",
  "target_process_id": "primary",
  "reason": "Add a merge-repair task after child import found conflicts.",
  "risk_class": "git_destructive",
  "requires_human_approval": true,
  "flow_patch_ref": "artifacts/amendments/amend_000001.patch",
  "evidence_refs": [],
  "created_at": "2026-06-09T12:00:00Z"
}
```

Default human approval is required only for very dangerous classes:

- secrets/auth changes;
- destructive git operations;
- irreversible external effects;
- removing or weakening acceptance criteria;
- removing a human gate;
- force-merging or closing external issue/PR state.

Everything else is configurable and can be performed by the workflow owner
without human approval.

### 6. Task Intake And Initialization Are Separate

Keep the phase boundary clear:

- **Task intake** records the human request, target agent capability analysis,
  recommended feature settings, and the recommended initialization prompt.
- **Initialization** creates the goal contract, root process, root `flow.toml`,
  process topology, initial mailboxes, test/eval tasks, feature overrides, and
  first execution brief.

Task intake may suggest a goal contract template. It does not create the final
goal contract.

### 7. Tests And Evals Are Workflow Tasks

Tests/evals are tasks in `flow.toml`, not transition-tool behavior.

Example:

```toml
[[tasks]]
task_id = "run-unit-tests"
role = "eval"
required_for = ["review", "completion"]
produces = ["artifacts/evals/unit-tests.json"]
```

Execution processes run the task and write evidence. Transition validation only
checks that declared evidence exists and satisfies gates.

System tests are selected during Initialization when the task is high risk,
cross-process, user-facing, or explicitly requested.

### 8. Prompt And Skill Quality Is Improved By Skills

Do not write a rigid prompt/skill validator.

Add installable skills:

- `rate-prompt-template`;
- `improve-skill-body`;
- `configure-long-horizon-features`;
- `plan-long-horizon-install`;

Skill quality rubric:

- explicit purpose and scope;
- required reads;
- allowed writes;
- sequential workflow;
- produced artifacts;
- commands/tools used;
- review and failure handling;
- completion evidence;
- concrete examples;
- no hidden implementation work inside planning-only prompts.

These skills should help an agent create strict enough prompts/templates for a
specific task while still allowing repo/task-specific flexibility.

### 9. GitHub Channel Must Be Full, Not Deferred

Implement GitHub as virtual channel processes with full issue and PR support.

Required operations:

- create issue;
- comment on issue;
- close issue;
- create PR;
- comment on PR;
- close PR;
- import issue comments;
- import PR comments;
- record delivery/import events in process mailboxes and logs.

Use repo-local GitHub auth rules already defined in `.agents/rules` and the
GitHub adapter. The channel should complain with setup instructions if no local
auth/config is available.

### 10. Deposition Writes Maintained Skills/Rules/Memory

Deposition is a workflow task. It may directly update:

- `.agents/skills/<skill>/SKILL.md`;
- `.agents/rules/*.md`;
- memory files;
- adapter templates.

It must also write review artifacts under `.long-horizon/` with:

- problem solved;
- usage evidence;
- scope and limits;
- counterexamples;
- validation performed;
- changed files;
- rollback instructions.

Human approval is not required by default except for dangerous classes.

Add separate deposition templates:

- `promote-skill.md`;
- `promote-rule.md`;
- `promote-memory.md`;
- `promote-adapter.md`;

### 11. Merge Conflict Repair Is A Workflow

Merge-conflict handling should be implemented as a detailed workflow template,
not a static policy.

The implementation goal should first research source-backed best practices for
merge conflict resolution, then create a template that:

- prefers a child workspace process for repair;
- allows parent process repair when configured;
- inspects parent, child, base, and conflict markers;
- preserves parent and child intent;
- produces a proposed patch before applying it;
- runs selected eval tasks;
- records merge-quality evidence;
- only applies/merges after approval when the action is dangerous.

## Revised Implementation Goal Shape

The next implementation goal should ask Codex `/goal` to complete v1 by doing
the following:

1. Replace hard-coded operation modes with small feature settings and derived
   profile/responsibility summaries.
2. Add install/task-level configuration skills for choosing feature settings.
3. Reduce process kinds to `workspace` and `virtual`.
4. Model external channels as virtual processes and supervision as runtime
   configuration.
5. Implement per-process FIFO mailboxes with durable JSONL inbox/outbox/ack
   files.
6. Rework human comments, observer interventions, process messages, and GitHub
   channel traffic onto the mailbox model.
7. Rework task setup into task intake and move goal contract/workflow creation
   into Initialization.
8. Replace versioned workflow state with one copied `flow.toml` per process and
   append-only amendment logs.
9. Keep tests/evals as workflow tasks; transition validation only verifies
   evidence.
10. Add prompt/skill rating and improvement skills with examples.
11. Remove slide compatibility artifacts.
12. Implement full GitHub issue/PR channel operations and inbound imports.
13. Add detailed deposition templates for skill/rule/memory/adapter promotion.
14. Add source-backed merge-conflict workflow template and proposed-patch flow.
15. Update README, STATUS, config catalog, skills, prompts, reports, and tests.

## Remaining Decisions Before Final Goal Document

Only a few decisions remain:

1. Should `message_mailboxes` always be enabled when `runtime_state = true`, or
   can a runtime-state task disable process messaging?

   Recommendation: always enable it. Mailboxes are the common substrate for
   human input, observer steering, GitHub comments, and process coordination.

2. Should each process mailbox be physically local to that process directory, or
   should there also be a run-level router ledger?

   Recommendation: keep physical inbox/outbox/ack files under each process
   directory and optionally add a generated run-level view for reporting. Do not
   make the run-level view authoritative.

3. Should GitHub PR creation be implemented by the runtime itself, or by a
   generated brief that instructs the target agent to use existing repo GitHub
   skills?

   Recommendation: both. The virtual GitHub process defines the operation
   envelope and artifacts. The adapter can either call `gh`/connector directly
   or emit a strict brief for a target agent when direct mutation is not
   available.

Your answers:

```text

1. agree
2. must keep physical inbox/outbox/ack files under each process; besides, the messages must be included in reporting data and viewer.
3. the virtual github process can also use the existing repo github skills.

```
