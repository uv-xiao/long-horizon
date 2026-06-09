# V1 Upgrade Negotiation Worksheet

This is a working document for turning the `STATUS.md` review comments into a
strong v1 upgrade goal. It is not the final implementation contract yet.

Fill the `Your answer` fields. Leave or edit the recommendations as needed.

## Current Diagnosis

The current v1 runtime is useful, but several concepts are still too coarse or
too isolated:

- operation modes are hard-coded labels instead of a flexible feature
  configuration;
- human comments, observer interventions, process communication, and external
  notifications are related but not unified;
- prompts and skills exist, but need stricter quality contracts;
- task setup, goal contract, flow assembly, and dynamic workflow amendment need
  clearer phase boundaries;
- tests/evals need a clearer place in goal contracts and workflow gates;
- some planned items are really process templates or sidecar processes, not
  always-on runtime mechanisms.

## My Direct Answers

### Do we need a real supervisor?

My answer: not always.

The supervisor should be a feature toggle, not a default requirement. If the
target agent already has reliable orchestration, we should use native-agent or
prompt-guided execution. If the target agent lacks orchestration, or if the task
requires long-running monitor/actor/critic processes, we enable a supervisor or
adapter-backed process runner.

Your answer:

```text
So what should the template's code become? Should we add real supervisor implementation to support the cases that the configuration decides on long-running processes?
```

### Is operation-mode provenance necessary?

My answer: yes, but the source of truth should change.

The current labels `runtime-owned`, `native-agent`, and `hybrid` are too coarse
as hard-coded modes. Provenance is still valuable if it records actual feature
toggles and responsibility split. Mode names should become derived summaries,
not primary policy.

Your answer:

```text
The terms used here are very confusing. If we're talking about feature toggles, why we say provenance, policy, ...? Make this more clear and intuitive for my better understanding.
```

### Should observer, human comment, and process communication be unified?

My answer: yes.

Human, observer, actor, critic, reporter, GitHub, and system watchdog can all
be modeled as processes or virtual processes that send typed messages. Human
comments become messages from a virtual `human` process or from an external
channel process such as `github-pr`.

Your answer:

```text
I think human-agent interaction can be handled all in the primary process. While others (like `github`) can become virtual process. The current process/workspace binding seems not complete: sidecar/external processes should be virtual, which doesn't own workspace, but only has a place to save things (logging and others).
```

## Upgrade Proposal

### 1. Replace Hard-Coded Operation Modes With Feature Toggles

Recommendation:

Use feature toggles as the canonical config. Operation modes become derived
profiles that explain a common configuration.

Possible feature toggles:

- `runtime_state`
- `prompt_templates`
- `transition_validation`
- `process_supervisor`
- `native_loop`
- `message_bus`
- `observer_processes`
- `report_server`
- `github_notifications`
- `artifact_retention_sidecar`
- `ledger_repair_process`
- `merge_repair_workflow`
- `deposition_workflow`

Example:

```toml
[features]
runtime_state = true
prompt_templates = true
transition_validation = true
process_supervisor = false
native_loop = true
message_bus = true
observer_processes = true
report_server = true
github_notifications = false
```

Open decisions:

1. Should feature toggles be the only source of truth, with mode names only
   derived labels?
2. Should toggles be global install defaults, task-level overrides, or both?
3. Which features must be enabled by default for a normal Codex `/goal` task?

Your answer:
```text

1. Is it enough for the configuration to ony decide on toggles? If so, use that as source of truth.
2. both, and we need skills to guide.
3. propose your solution.

Also, some features should not be harded. For example, observer_processes can be created by task/goal/workflow design, not a feature from the template. We should keep the features essential and tiny (not covering anything to be set up as goal/workflow)
```

### 2. Add A Unified Process And Message Model

Recommendation:

Define all actors as processes:

- task process;
- parent process;
- child process;
- observer process;
- actor process;
- critic process;
- reporter process;
- human virtual process;
- GitHub channel process;
- external agent process.

Define all communication as typed messages:

- `source_process_id`
- `target_process_id`
- `message_type`
- `thread_id`
- `body`
- `artifact_refs`
- `causal_refs`
- `delivery_channel`
- `delivery_status`
- `ack_status`
- `created_at`
- `delivered_at`

This should unify:

- observer interventions;
- human comments;
- process-to-process messages;
- actor/critic communication;
- GitHub issue/PR comments;
- reporter questions or annotations.

Open decisions:

1. Should every human comment become a message from a virtual `human` process?
2. Should GitHub issue/PR comments be a channel process, a human process input,
   or both?
3. Should messages be append-only only, or should there also be a mutable
   per-thread latest-state board?
4. Should acknowledgements be required for steering messages by default?

Your answer:

```text
1. we use a primary process as human entry.
2. a virtual process (we use workspace/virtual process naming).
3. append-only.
4. not sure. but I think we messages be async to improve system robustness.
```

### 3. Clarify Phase Boundaries

Recommendation:

Use these phase meanings:

- **Task setup**: intake, task profile, target-agent capability fit,
  feature-toggle selection, initial process topology.
- **Goal contract**: durable objective, hard constraints, open search space,
  acceptance criteria, evidence requirements, human decision points.
- **Flow assembly**: states, transitions, gates, process topology, message
  topology, tests/evals, dynamic amendment policy.
- **Execution**: processes produce artifacts, send messages, run checks, and
  request transitions.
- **Review/completion/deposition**: evidence audit, PR/code review, skill or
  memory promotion, adapter promotion, methodology deposition.

Open decisions:

1. Should task setup always produce a goal contract scaffold, or only when the
   task is accepted?
2. Should dynamic workflow amendment live in flow assembly, live operation, or
   both?
3. Should a workflow amendment always create a new flow snapshot?

Your answer:

```text
I think we can merge flow assemby into goal contract. It should be a comprehensive "Initialization" step. 
This is because the workflow might not be static, so a standalone flow assembly might not do much work like creating a complete workflow.
Also, I don't think the "Review/completion/deposition" should be a standalone phase. They should be steps / tasks in the workflows.

Why the task setup should generates a goal contract? goal contract should be part of initialization. Explain this for me.
For dynamic workflow, I think it should has init workflow assembly at initialization, while provding tools with skills for dynamic adjustment during execution.
I think the fixed flow.toml and snapshot mechanism should be just remoted by the native dynamic workflow. The workflow is a copy-or-write thing to be maintained and updated by each process. 

```

### 4. Support Dynamic Workflow Amendment

Recommendation:

Dynamic workflow changes should be explicit amendment artifacts, not silent
edits. A workflow amendment should include:

- reason;
- old flow ref;
- proposed flow diff;
- affected states/gates/processes/messages;
- impact on active children;
- required approvals;
- validation results;
- new flow snapshot id;
- rollback path.

Default policy: human approval is required when the amendment changes goal
constraints, acceptance evidence, safety boundaries, human gates, or process
topology.

Open decisions:

1. Should dynamic workflow amendment require human approval by default?
2. Can low-risk amendments be auto-applied by the parent process?
3. Should active child processes inherit amendments automatically, only by
   rebrief, or only by respawn?

Your answer:

```text
1. no.
2. why parent process?
3. I think only by respawn.
```

### 5. Position Tests And Evals

Recommendation:

Tests/evals should be configured in the goal contract and flow assembly:

- Goal contract defines required correctness checks, metrics, acceptance
  evidence, and promotion criteria.
- Flow assembly attaches checks/evals to states and transitions.
- Transition validation executes or verifies gate evidence.
- System tests are workflow-level acceptance/eval artifacts, not generic helper
  tests.

Open decisions:

1. Should tests/evals be declared as artifacts, commands, adapters, or all
   three?
2. Should transition tooling run checks directly, or only verify check-result
   events produced by processes?
3. Should system tests be mandatory for every long-horizon task, or only for
   high-risk/complex tasks?

Your answer:

```text
1. they should just be tasks first. For detailed commands to trigger specific test/eval, it can be deposited as skills/adapters composition.
I don't think tests/evals should be run during transitions. They should be tasks running on state.
system tests should not be mandatory. It's optional, configured according to LLM decisions.

```

### 6. Strengthen Prompt And Skill Quality Contracts

Recommendation:

Every prompt template and skill should satisfy a validator contract:

- hard constraints;
- allowed writes;
- required reads;
- sequential phases;
- required artifacts;
- required commands or validators;
- review gate;
- failure handling;
- completion evidence;
- no hidden implementation work during planning-only phases.

Open decisions:

1. Should we write a validator that checks every prompt/skill for these
   sections?
2. Should missing sections fail tests?
3. Should skills include examples, or should examples live in separate
   templates?

Your answer:

```text
We can add a prompt template / skill body rating and improving skill.
No need to write a validator program since it might be too restricted.
skills should include examples.

```

### 7. Remove Deprecated Slide Artifacts

Recommendation:

Remove `slides.html` and `slides-data.json` compatibility aliases from v1.
Keep:

- `progress.html`;
- `progress.md`;
- `report-data.json`.

Open decisions:

1. Remove slide compatibility now?
2. Keep redirects for one more transition period?

Your answer:

```text
Remove. We just let progress.{html, md} to show the stepping history.

```

### 8. Define Notification Interface, GitHub First

Recommendation:

Create a generic notification/channel interface, then implement GitHub as the
first real channel:

- GitHub issue comments;
- GitHub PR comments;
- status/report link comments;
- inbound comment import as messages;
- ack/delivery records in message ledgers.

Open decisions:

1. Should GitHub issues, PR comments, or both be implemented first?
2. Should notifications be push-only, pull-only, or bidirectional?
3. Should notification channels be processes in the process/message model?

Your answer:

```text
1. both. It can create/comment/close/... issues and PRs;
2. it should be general inter-process message. As for message's implementation manner, we need a standalone, detailed discussion.
3. sure.
```

### 9. Add Detailed Deposition Templates

Recommendation:

Skill/memory/adapter promotion should be a rich template-guided review process.
Promoted knowledge should include:

- specific problem;
- reusable context;
- exact solution or rule;
- applicability conditions;
- counterexamples;
- validation evidence;
- rollback/removal criteria;
- where it should be installed;
- owner/review metadata.

Open decisions:

1. Should promoted skills be written directly into `.agents/skills/`, or first
   staged under `.long-horizon/artifacts/deposition/` for review?
2. Should memory/rule/skill promotion share one template or have separate
   templates?
3. Should promotion require human approval by default?

Your answer:

```text

I think directly into `.agents/skills` for immediate adoption by agents; but this should not be just append-only. We need carefully maintained skill directory. Also, the review should be carefully conducted by agents at least during the deposition tasks.
Separte, and what product should the promotion generate should by LLM-guided.
No; long-running works should need less human intervention.
```

### 10. Add Detailed Merge-Conflict Workflow Templates

Recommendation:

Merge-conflict handling should be a workflow step with expert guidance, not a
single policy. It should cover:

- base/head/child branch inspection;
- conflict classification;
- intent preservation;
- test/eval selection;
- conflict resolution strategy;
- parent and child evidence preservation;
- rollback;
- review handoff;
- merge-quality acceptance criteria.

Open decisions:

1. Should we browse/research external merge-conflict best practices before
   writing this template?
2. Should merge repair be allowed to edit code directly, or produce a proposed
   patch for review first?
3. Should merge repair run in a child process/worktree by default?

Your answer:

```text
1. yes
2. review first;
3. I think spawn a child process is good. But doing it in parent process should also be allowed.

```

## Proposed Upgrade Goal Shape

After your answers, the implementation goal should likely be:

1. Add feature-toggle config and derived profile reporting.
2. Add a unified process/message model.
3. Rewrite capability analysis to choose feature toggles, not hard-coded modes.
4. Update install/task setup/brief/report to expose feature responsibilities.
5. Add prompt/skill validators.
6. Strengthen install/capability/configuration skills.
7. Add dynamic workflow amendment artifacts and validators.
8. Remove slide compatibility artifacts if approved.
9. Add notification interface with GitHub first if approved.
10. Add rich deposition and merge-conflict templates.
11. Update `STATUS.md`, README, docs, and system tests.

Your edits to this plan:

```text
Re-propose according to my comments above.
```
