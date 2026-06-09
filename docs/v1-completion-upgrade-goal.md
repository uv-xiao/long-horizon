# V1 Completion Upgrade Goal

This document is the implementation-facing goal for completing v1 after the
review rounds captured in `docs/v1-upgrade-negotiation-r3.md`.

It supersedes the older mode/version/message-thread ideas for the next
implementation slice. Keep v1 as the product line. Do not rename this work into
a separate product line.

## Objective

Complete v1 by making the long-horizon template easier to install, configure,
run, observe, and evolve while keeping the runtime model simple:

- feature settings are the source of truth;
- process kinds are only `workspace` and `virtual`;
- process communication uses per-process FIFO mailboxes;
- each process owns one current `flow.toml`;
- child processes get copy-on-write state by copying process files at spawn;
- GitHub issue/PR interaction is implemented as virtual channel processes;
- prompts and skills guide setup, configuration, deposition, and repair.

The implementation must preserve the existing principle: Codex `/goal` or any
other agent is an execution substrate adapter. The long-horizon template owns
contracts, state, validation, mailboxes, reports, and evidence.

## Required Reads

Read these first:

- `AGENTS.md`
- `README.md`
- `STATUS.md`
- `docs/v1-runtime-implementation-spec.md`
- `docs/v1-template-usability-goal.md`
- `docs/v1-upgrade-negotiation-r3.md`
- `templates/.long-horizon/config-catalog.md`
- `.agents/skills/evolve-long-horizon-template/SKILL.md`
- `.agents/skills/git-commit/SKILL.md`
- `.agents/rules/github-cli.md`

If any file conflicts with this goal, this goal wins for the upgrade slice.

## Non-Negotiable Design Decisions

### Feature Settings

Replace hard-coded operation modes as source of truth with small feature
settings:

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

Rules:

- `transition_validation = true` whenever `runtime_state = true`.
- `message_mailboxes = true` whenever `runtime_state = true`.
- Operation/profile names may remain only as derived labels in reports,
  decision records, and briefs.
- Do not add global feature toggles for observer, actor, critic, deposition, or
  retention. Those are workflow-created roles/tasks.

### Process Model

Use only two process kinds:

- `workspace`: owns or attaches to a repo directory or git worktree.
- `virtual`: owns state, logs, mailboxes, and optional adapter metadata, but no
  workspace.

External services are virtual processes. Supervision is runtime configuration,
not a process kind.

Required process record fields:

- `process_id`
- `process_kind`
- `role`
- `parent_process_id`
- `state_path`
- `workspace_path`
- optional `branch`
- optional `[adapter]`
- optional `[runtime]`

### Mailboxes

Implement per-process FIFO mailboxes:

```text
.long-horizon/goals/<goal>/runs/<run>/processes/<process-id>/mailbox/
  inbox.jsonl
  outbox.jsonl
  ack.jsonl
```

Required behavior:

- sending appends to source `outbox.jsonl`;
- delivery appends to target `inbox.jsonl`;
- acknowledgements append to target/source `ack.jsonl` as appropriate;
- FIFO order is per target inbox;
- delivery is async;
- mailboxes are file-backed when `local_supervisor = false`;
- a future supervisor may use in-memory queues only if it still flushes durable
  JSONL records;
- reports must include mailbox data and communication links.

Do not implement message threads or a mutable thread board in this slice.

### Workflow State

Use one current workflow file per process:

```text
.long-horizon/goals/<goal>/runs/<run>/processes/<process-id>/flow.toml
.long-horizon/goals/<goal>/runs/<run>/processes/<process-id>/flow-amendments.jsonl
```

Initialization creates root `flow.toml` when `runtime_state = true`.

Copy-on-write rule:

- spawn copies the parent's process state, including `flow.toml`, into the
  child process state directory;
- the child may amend its own `flow.toml`;
- the parent does not automatically adopt child amendments;
- join/import inspects child artifacts, messages, amendments, and flow before
  adopting changes.

Do not implement versioned workflow directories for this slice.

### Workflow Amendment

Use `workflow owner process` as the authority term.

Human approval is required by default only for dangerous actions:

- secrets/auth changes;
- destructive git operations;
- irreversible external effects;
- removing or weakening acceptance criteria;
- removing a human gate;
- force-merging or closing external issue/PR state.

Other workflow amendments can be performed by the workflow owner and recorded
in `flow-amendments.jsonl`.

### Task Intake And Initialization

Separate these phases:

- **Task intake** records the human request, target-agent capability analysis,
  recommended feature settings, and the recommended initialization prompt.
- **Initialization** creates the goal contract, root process, root `flow.toml`,
  process topology, mailboxes, tests/eval tasks, feature overrides, and first
  execution brief.

Task intake may suggest templates. It must not pretend the final goal contract
already exists.

### Tests And Evals

Tests and evals are workflow tasks. Transition validation must verify evidence;
it must not run tests/evals itself.

System tests should be selected during Initialization when the task is high
risk, cross-process, user-facing, or explicitly requested.

### GitHub Channel

Implement GitHub issue and PR channels as virtual processes.

Required operations:

- create issue;
- comment on issue;
- close issue;
- create PR;
- comment on PR;
- close PR;
- import issue comments;
- import PR comments;
- record outbound, inbound, delivery, and failure events in mailboxes/logs.

The virtual GitHub process may call the runtime adapter directly or use existing
repo GitHub skills through a generated strict brief. It must obey repo-local
GitHub auth rules and must not silently fall back to global auth.

### Prompt, Skill, And Deposition Layer

Add or update installable skills/templates for:

- configuring feature settings;
- planning installation;
- rating prompt templates;
- improving skill bodies;
- promoting skills;
- promoting rules;
- promoting memory;
- promoting adapters;
- merge-conflict repair.

Skill/template quality requirements:

- explicit purpose and scope;
- required reads;
- allowed writes;
- sequential workflow;
- produced artifacts;
- commands/tools used;
- review/failure handling;
- completion evidence;
- concrete examples.

Deposition may directly update `.agents/skills`, `.agents/rules`, memory files,
or adapter templates when the agent judges promotion is ready. It must also
write review evidence under `.long-horizon/`.

### Reports

Remove slide compatibility artifacts. Keep:

- `progress.html`
- `progress.md`
- `report-data.json`

Reports must include:

- process topology;
- process kind and role;
- current process `flow.toml` state;
- workflow amendments;
- mailbox messages and communication links;
- human comments and GitHub channel events;
- observer/intervention events;
- child spawn/join/import evidence;
- dangerous-action approval evidence when present.

The current report UI may remain plain. Add explicit future status notes that a
richer GUI adapter can later render the same `report-data.json`.

## Implementation Tasks

1. Update config parsing/validation to support feature settings and derived
   profile/responsibility summaries.
2. Replace operation-mode source-of-truth behavior with feature settings while
   keeping backward compatibility where practical.
3. Update process metadata to support only `workspace` and `virtual`.
4. Implement mailbox APIs and CLI commands for send, deliver, receive/list, and
   ack.
5. Route human comments, observer interventions, process messages, and GitHub
   events through mailboxes.
6. Rework task setup into task intake and move goal contract/workflow creation
   into Initialization artifacts.
7. Move from run-level workflow snapshots as the primary model to per-process
   `flow.toml`.
8. Implement child spawn copy-on-write for process state and per-process flow.
9. Implement append-only `flow-amendments.jsonl` and workflow owner amendment
   records.
10. Ensure transition validation checks evidence against the relevant process
    `flow.toml`.
11. Add full GitHub issue/PR channel operations and inbound imports.
12. Add prompt/skill rating and improvement skills with examples.
13. Add detailed deposition templates for skill/rule/memory/adapter promotion.
14. Research merge conflict resolution best practices and add a source-backed
    merge-repair workflow template that produces a proposed patch first.
15. Remove `slides.html` and `slides-data.json` generation/tests/docs.
16. Update README, STATUS, config catalog, skills, prompts, reports, and tests.

## Testing And Acceptance Bar

Do not spend effort on shallow helper tests. Add tests that prove core runtime
behavior under realistic pressure.

Required unit tests:

- feature settings validation and backward-compatible mode derivation;
- process kind validation rejects anything except `workspace` and `virtual`;
- mailbox send/deliver/ack preserves FIFO and durable JSONL records;
- mailbox messages cannot drive transitions without declared evidence;
- per-process `flow.toml` transition validation;
- child spawn copies process state and child changes do not mutate parent state;
- workflow amendments require approval for dangerous classes;
- GitHub channel operation envelopes and auth failure guidance;
- report data includes mailboxes and process communication links.

Required system tests:

1. **Feature-settings install and compatibility**
   - create a temporary target repo with an older mode-based config fixture;
   - run install/update;
   - verify the new `[features]` table is written;
   - verify `runtime_state = true` forces `transition_validation = true` and
     `message_mailboxes = true`;
   - verify old operation-mode data is preserved only as a derived
     profile/responsibility summary;
   - verify `.long-horizon/install-plan.md`,
     `.long-horizon/agent-capabilities.toml`, and the config catalog explain
     the feature choices and override paths.
2. **Task intake to initialization**
   - run task intake with fixed fake-agent capability input;
   - verify intake records the human request, capability fit, recommended
     feature settings, and recommended initialization prompt;
   - run initialization from that intake;
   - verify initialization creates the goal contract, root workspace process,
     root `flow.toml`, process mailboxes, eval tasks, and first execution
     brief;
   - verify task intake did not create the final goal contract by itself;
   - verify reports and briefs explain feature settings and responsibility
     ownership.
3. **Two process kinds and virtual channels**
   - create one workspace process and one virtual process;
   - verify process validation rejects `external`, `supervised`, or any other
     process kind;
   - attach adapter metadata to the virtual process for a fake GitHub channel;
   - verify the virtual process owns state/mailboxes/logs and has no workspace;
   - verify supervision metadata can be configured without changing the process
     kind.
4. **Mailbox FIFO and process communication**
   - create primary, actor, critic, observer, human, and GitHub virtual/channel
     processes;
   - send multiple messages to the same target process and verify inbox FIFO
     order;
   - ack one message and leave another unacked;
   - verify ack state is append-only and does not block mailbox delivery;
   - verify a mailbox message alone cannot satisfy a transition unless the
     relevant `flow.toml` gate declares that message/evidence requirement;
   - verify generated report data contains the mailbox messages and
     communication links.
5. **Monitor actor critic**
   - root/monitor process spawns actor and critic workspace processes;
   - actor and critic exchange mailbox messages using fixed fake-agent IO;
   - monitor observes mailbox/process state and sends steering messages;
   - actor follows one steering message and writes evidence;
   - critic challenges actor output and writes review evidence;
   - join imports child evidence without auto-adopting child `flow.toml`
     changes;
   - verify parent, actor, critic, and monitor roles are visible in report data.
6. **Humanize-style fork join**
   - mimic a two-loop Humanize-style workflow with fixed fake-agent IO;
   - outer loop creates a benchmark/eval task and a review task;
   - inner loop forks at least three child explorations;
   - children produce fixed artifacts, eval outputs, and mailbox messages;
   - parent joins children, evaluates evidence, chooses one result, and records
     why the others were rejected;
   - parent amends its own `flow.toml` if the fixed evidence requires another
     loop;
   - verify completion only happens after declared eval/review evidence exists.
7. **Second-generation Humanize-style workflow example**
   - create a workflow that combines process topology, eval tasks, observer
     steering, human comment import, and dynamic flow amendment;
   - use fixed inputs/outputs to mimic a real agent run instead of relying on
     live LLM behavior;
   - include a virtual human process that sends a review comment to the primary
     process;
   - include an observer process that sends an append-only intervention;
   - verify the primary process responds through mailbox evidence and continues
     the workflow correctly.
8. **Copy-on-write per-process flow**
   - spawn a child process/worktree from the parent;
   - verify child process state receives a copied `flow.toml`, mailbox
     directory, and relevant process metadata;
   - modify child `flow.toml`, append child amendments, add child mailbox
     messages, and write child artifacts;
   - verify parent state is unchanged before join/import;
   - run explicit join/import;
   - verify imported artifacts and any adopted flow changes carry provenance.
9. **Dangerous amendment approval**
   - attempt a destructive git amendment or acceptance-criteria weakening
     amendment;
   - verify it is classified as dangerous and blocks without human approval
     evidence;
   - add fixed human approval evidence through the mailbox/comment path;
   - verify the amendment applies, records approval evidence, and appears in
     `report-data.json`, `progress.md`, and `progress.html`.
10. **Full GitHub virtual channel**
    - run with fixed GitHub adapter input and local-auth fixtures;
    - create/comment/close issue operation envelopes;
    - create/comment/close PR operation envelopes;
    - import fixed issue and PR comments;
    - route outbound and inbound events through the GitHub virtual process
      mailbox;
    - verify failures from missing local `gh` auth produce setup guidance and do
      not fall back silently to global auth;
    - verify the GitHub virtual process can also generate a strict brief that
      tells an agent to use existing repo GitHub skills for the same operation.
11. **Prompt, skill, and install usability**
    - verify installed skills include configuration, install planning,
      prompt-template rating, and skill-body improvement;
    - run the rating/improvement flow against a deliberately weak prompt
      fixture;
    - verify the improved prompt has purpose/scope, required reads, allowed
      writes, sequential steps, produced artifacts, failure handling, completion
      evidence, and examples;
    - verify install/configuration skills produce a decision artifact rather
      than silently mutating policy.
12. **Deposition promotion**
    - run a fixed task that logs a learned adapter or lesson under run
      artifacts;
    - execute promotion templates for skill, rule, memory, and adapter cases;
    - verify maintained outputs are written to `.agents/skills`,
      `.agents/rules`, memory files, or adapter templates as appropriate;
    - verify review artifacts under `.long-horizon/` record problem, evidence,
      scope, counterexamples, validation, changed files, and rollback;
    - verify dangerous promotions require approval, while normal promotions do
      not by default.
13. **Merge-conflict repair workflow**
    - create parent and child branches with a deterministic merge conflict;
    - spawn or use a repair workspace process;
    - run the merge-repair template with fixed research/source notes available
      as test fixtures;
    - verify the workflow inspects base, parent, child, and conflict markers;
    - verify it writes a proposed patch before applying anything;
    - verify selected eval tasks run against the proposed patch;
    - verify dangerous merge application requires approval evidence;
    - verify the final merge or blocked result records merge-quality evidence.
14. **Report completeness and no slide artifacts**
    - generate `progress.html`, `progress.md`, and `report-data.json`;
    - verify `slides.html` and `slides-data.json` are not generated;
    - verify report data includes feature settings, derived profile,
      responsibility map, process topology, process kinds, per-process
      `flow.toml` state, amendments, mailbox links, human/GitHub comments,
      observer interventions, child spawn/join/import evidence, dangerous
      approvals, deposition events, and merge-repair evidence;
    - verify the HTML and Markdown views expose enough anchors and labels for a
      human reviewer to inspect those artifacts manually.
15. **End-to-end hard acceptance**
    - run one full fake-agent scenario that combines install, task intake,
      initialization, monitor/actor/critic, fork/join, mailbox communication,
      human/GitHub comments, copy-on-write flow, dangerous approval, deposition,
      report generation, and completion audit;
    - verify the scenario uses fixed inputs/outputs and deterministic fake
      agents;
    - verify completion fails if any required artifact, mailbox event, approval,
      or eval evidence is removed.

Acceptance requires the tests above to pass or any intentionally deferred gap to
be explicitly recorded in `STATUS.md` with rationale and a follow-up path.

## Documentation Updates

Update public docs after implementation:

- `README.md`: structured v1 design by phase, mechanism, and component.
- `STATUS.md`: implemented, partial, planned, and outdated items.
- `templates/.long-horizon/config-catalog.md`: feature settings and
  configuration skills.
- `CHANGELOG.md`: commit/PR-sized public design and implementation changes.

Do not put private scratch paths, raw research acquisition notes, or temporary
review logs in public docs.

## Completion Criteria

The upgrade is complete only when:

- implementation tasks are done or explicitly recorded as deferred in
  `STATUS.md`;
- all required tests pass;
- reports are generated without slide artifacts;
- GitHub channel behavior is tested with fixed inputs and local auth failure
  paths;
- docs and skills match the final design;
- changes are committed cleanly.

## Suggested `/goal` Prompt

```text
Implement the v1 completion upgrade for this repo.

Repo: /home/uvxiao/long-horizon
Branch: feat/first-version-implementation

Strict source of truth:
- docs/v1-completion-upgrade-goal.md

Read first:
- AGENTS.md
- docs/v1-completion-upgrade-goal.md
- docs/v1-runtime-implementation-spec.md
- docs/v1-template-usability-goal.md
- docs/v1-upgrade-negotiation-r3.md
- README.md
- STATUS.md
- templates/.long-horizon/config-catalog.md
- .agents/skills/evolve-long-horizon-template/SKILL.md
- .agents/skills/git-commit/SKILL.md

Rules:
- Keep this as v1 completion work, not a separate product line.
- Follow docs/v1-completion-upgrade-goal.md strictly.
- If older docs conflict with the goal doc, the goal doc wins.
- If blocked, exploit practical alternatives that preserve the architecture and
  make the end-to-end mechanism work. Record intentional gaps in STATUS.md.
- Do not mention ignored local scratch paths in public docs.
- Update CHANGELOG.md.

Testing bar:
- Do not add shallow tests for unimportant helpers.
- Add focused unit tests for mechanism boundaries.
- Add every required system test listed in the Testing And Acceptance Bar:
  feature-settings install/compatibility, task intake/initialization, process
  kinds, mailbox FIFO, monitor/actor/critic, Humanize-style fork/join,
  second-generation Humanize-style workflow, copy-on-write flow, dangerous
  amendment approval, full GitHub channel, prompt/skill usability, deposition
  promotion, merge-conflict repair, report completeness, and end-to-end hard
  acceptance.

Finish:
- Run tests and a useful demo CLI flow.
- Commit cleanly and push.
- Final response: capabilities implemented, test results, deferred STATUS
  items, commit hash.
```
