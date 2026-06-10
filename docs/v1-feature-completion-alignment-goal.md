# V1 Feature Completion And Alignment Goal

This document is the next implementation-facing goal for making the newly added
v1 features truly complete. It exists because the current branch added useful
runtime primitives, but several public docs now overstate completion before the
mechanisms have been proven end to end.

This is still v1. Do not rename this work into a new version line.

## Objective

Bring the implementation, installable prompt/skill layer, tests, reports, and
public docs into strict alignment with `docs/v1-completion-upgrade-goal.md`.

Completion means each newly added feature is represented as a coherent v1
mechanism, not merely as a Python module or CLI command:

- runtime behavior exists and is wired into the process/workflow model;
- installable prompts or skills guide agents and humans through correct use;
- durable artifacts and ledgers prove what happened;
- reports expose the behavior for human review;
- system tests exercise realistic fixed-agent scenarios;
- public docs and `STATUS.md` only claim what the evidence proves.

## Required Reads

Read these first:

- `AGENTS.md`
- `README.md`
- `STATUS.md`
- `docs/v1-completion-upgrade-goal.md`
- `docs/v1-runtime-implementation-spec.md`
- `docs/v1-template-usability-goal.md`
- `docs/v1-system-test-coverage.md`
- `docs/v1-implementation-verification-guide.md`
- `templates/.long-horizon/config-catalog.md`
- `.agents/skills/evolve-long-horizon-template/SKILL.md`
- `.agents/skills/git-commit/SKILL.md`

If any file conflicts with `docs/v1-completion-upgrade-goal.md`, that goal wins
for design. If this document conflicts with that goal, fix this document or the
implementation plan rather than weakening the negotiated goal.

## Current Problem To Fix

The current branch has provisional runtime modules for local supervision,
notification, evaluation, promotion, retention, ledger recovery, merge repair,
and report GUI manifests. Those modules may be a good substrate, but they do
not by themselves satisfy the negotiated design.

The main alignment failures to audit and fix are:

- `STATUS.md` claims every v1 mechanism is implemented before the new features
  have full runtime, prompt/skill, report, and system-test evidence.
- Several new features are isolated Python surfaces rather than integrated
  workflow steps with process ownership, mailboxes, approvals, and durable
  completion evidence.
- Tests currently risk proving command availability instead of proving the
  full long-horizon behavior required by `docs/v1-completion-upgrade-goal.md`.
- Promotion/deposition must be exercised through installable skills/templates
  and review artifacts, not only direct Python writes.
- Merge-conflict repair must be source-backed and branch-aware: base, parent,
  child, conflict markers, proposed patch, eval gates, approval, and final
  apply/block evidence must all be represented.
- GitHub virtual channel behavior must record durable success and failure
  envelopes through virtual process mailboxes and must obey local auth rules.
- Reports must show the new feature families as first-class reviewable process,
  event, artifact, and communication data, not only generic event rows.
- The config catalog, README, verification guide, and system-test coverage docs
  must not describe stronger behavior than the runtime and tests actually
  prove.

## Non-Negotiable Design Anchors

Do not weaken these decisions while completing the feature set:

- feature settings are the source of truth;
- process kinds are only `workspace` and `virtual`;
- process communication uses per-process FIFO mailboxes;
- each process owns one current `flow.toml`;
- child processes receive copy-on-write process state by copying files at
  spawn;
- GitHub issue/PR interaction is implemented as virtual channel processes;
- tests and evals are workflow tasks, while transition validation only verifies
  recorded evidence;
- prompts and skills guide setup, configuration, deposition, repair, and
  operation;
- reports are `progress.html`, `progress.md`, and `report-data.json`;
- no slide compatibility artifacts are restored;
- Codex `/goal` or any other agent remains an execution substrate adapter, not
  the long-horizon system itself.

## Feature Completion Definition

A feature is complete only when all applicable layers are present:

1. **Model ownership**: the feature has a clear owner in the phase/mechanism/
   component architecture.
2. **Runtime behavior**: the feature performs real work through the v1 process,
   workflow, mailbox, artifact, and ledger model.
3. **Agent-facing use**: an installable prompt or skill tells an agent how to
   decide when to use it, what to read, what it may write, what evidence to
   produce, and how to handle failure.
4. **Human-facing review**: report data and Markdown/HTML views expose enough
   state, events, links, and artifacts for human inspection.
5. **System-test proof**: a hard system test demonstrates the mechanism in a
   realistic fixed-agent workflow, including failure paths when relevant.
6. **Documentation alignment**: `STATUS.md`, README, config catalog, and
   verification docs cite evidence that exists and matches the implementation.

Runtime-only code is not enough. Prompt-only guidance is not enough. A test that
only calls a helper or CLI command is not enough.

## Workstream 1: Requirement Matrix

Create a requirement matrix before changing behavior. The matrix may live in
`docs/v1-feature-completion-audit.md` or an equivalent public verification
document.

For every requirement in `docs/v1-completion-upgrade-goal.md`, record:

- requirement id or short name;
- source section;
- intended owner: phase, mechanism, or component;
- expected runtime files/modules;
- expected installable prompts/skills;
- expected durable artifacts and ledgers;
- expected report fields/views;
- expected unit tests;
- expected system tests;
- current status: missing, provisional, implemented, or overclaimed;
- action needed.

The matrix must explicitly cover the newly added feature families:

- local process supervisor;
- human notification channels;
- evaluation adapters;
- promotion/deposition;
- artifact retention sidecar;
- ledger integrity recovery;
- merge-conflict repair;
- report GUI adapter boundary;
- GitHub virtual channel success and failure envelopes;
- document-code-status alignment.

## Workstream 2: Runtime Integration

Audit each provisional runtime module and either complete, refactor, or remove
it. Keep only code that strengthens the negotiated v1 model.

### Local Supervisor

The supervisor must be runtime configuration and lifecycle support, not a third
process kind. Completion requires:

- process records stay `workspace` or `virtual`;
- subprocess start/status/reap/terminate events write durable process events;
- supervised handles record PID, command, cwd, logs, start time, exit status,
  and associated process id;
- interrupted or exited work can produce a regenerated brief or recovery event;
- tests show supervision metadata does not bypass workflow transitions.

### Notification Channels

Notifications must be virtual-channel communication, not an unrelated alert API.
Completion requires:

- local and GitHub-backed notifications are represented as virtual processes or
  messages routed through virtual process mailboxes;
- success and failure envelopes are durable;
- GitHub notifications obey repo-local auth rules and never silently fall back
  to global auth;
- human comments and notification responses can be imported as typed human
  events and mailbox messages;
- reports show notification events and target process links.

### Evaluation Adapters

Evaluations are workflow tasks. Completion requires:

- adapters write durable eval artifacts and events;
- transition validation only consumes eval evidence declared by `flow.toml`;
- fixed command, file, and metric adapters exist as v1 defaults;
- adapter failures are explicit evidence, not silent exceptions;
- reports expose eval task inputs, outputs, status, and process owner.

### Promotion And Deposition

Promotion is a workflow/skill process, not just a write helper. Completion
requires:

- installable skills/templates cover skill, rule, memory, and adapter
  promotion;
- promotion artifacts record problem, evidence, scope, counterexamples,
  validation, changed files, rollback plan, and approval when required;
- normal promotions can proceed without default human approval, while dangerous
  promotions are gated;
- learned adapters can be used immediately and logged under run artifacts;
- stable artifacts can be deposited into `.agents/skills`, `.agents/rules`,
  memory files, or adapter templates through the promotion workflow;
- rollback records and report events are generated.

### Artifact Retention Sidecar

Retention is a sidecar policy process. Completion requires:

- retention never silently deletes evidence needed for audit trust;
- compressed, archived, or externalized artifacts retain source lineage;
- manifests record original path, retained path, hash, size, policy, and reason;
- reports show retained artifacts and how to inspect or restore them;
- tests prove transitions and completion audits still trust retained evidence.

### Ledger Recovery

Ledger recovery is a privileged reconciliation workflow. Completion requires:

- damaged or partial ledgers are preserved before repair;
- recovered ledgers are written as reconciled outputs, not silent rewrites;
- reconciliation reports explain dropped, repaired, duplicated, or invalid
  records;
- recovery events are append-only and visible in reports;
- tests include damaged hash chains and partial-copy style ledgers.

### Merge-Conflict Repair

Merge repair must become a source-backed workflow step. Completion requires:

- deterministic conflict fixtures create parent and child branch states;
- repair reads base, parent, child, current conflict markers, and merge failure
  events;
- it writes a proposed patch before applying anything;
- configured evals run against the proposed patch;
- dangerous apply/force behavior requires approval evidence;
- final apply or block records merge-quality evidence;
- parent process owns inspect/join/merge authority over child processes.

### Report GUI Adapter Boundary

The v1 report remains human-only and should not spend extra LLM tokens. The GUI
adapter boundary must preserve report-data independence. Completion requires:

- `report-data.json` remains the durable data contract;
- `progress.html` and `progress.md` are generated from source-backed data;
- a GUI manifest records adapter name, version, supported data version, entry
  points, required assets, and unsupported features;
- no GUI-specific runtime state becomes canonical;
- richer future GUI work is documented as an adapter path, not as a v1 blocker.

## Workstream 3: Prompt, Skill, And Template Integration

Update or add installable prompts/skills so the new runtime mechanisms are
usable by a target agent or human operator.

Every new or updated skill must include:

- purpose and scope;
- required reads;
- allowed writes;
- sequential workflow;
- produced artifacts;
- commands or tools used;
- review and failure handling;
- completion evidence;
- concrete examples.

At minimum, cover:

- choosing stable runtime versus native-agent orchestration based on target
  agent capability analysis;
- operating or delegating the local supervisor;
- routing and importing human/GitHub notifications;
- selecting and recording eval adapters as workflow tasks;
- running promotion/deposition for skills, rules, memory, and adapters;
- starting and reviewing retention sidecars;
- reconciling damaged ledgers;
- repairing merge conflicts through a source-backed proposed-patch workflow;
- updating policy/configuration during installation or goal setup.

This work must make clear when the template provides a stable runtime and when
it only enables or briefs a target agent's native orchestration features.

## Workstream 4: Strong System Tests

Do not add shallow tests that only increase counts. Add tests that prove the
long-horizon system works under pressure with deterministic fake agents.

Required new or strengthened system tests:

1. **Full completion-upgrade acceptance scenario**
   - install into a temporary target repo;
   - run task intake and initialization;
   - create primary, monitor, actor, critic, observer, human virtual, and
     GitHub virtual processes;
   - route fixed fake-agent messages through mailboxes;
   - supervise at least one real local subprocess;
   - run eval adapters as workflow tasks;
   - fork child explorations and join selected evidence;
   - import human and GitHub comments;
   - perform a promotion/deposition;
   - run retention and ledger recovery sidecars;
   - generate reports;
   - prove completion fails when required evidence is removed.
2. **Humanize-style two-loop fork/join scenario**
   - mimic an outer benchmark/review loop and inner exploration loop;
   - fork at least three fixed child candidates;
   - evaluate and review candidates with fixed artifacts;
   - select one candidate and reject others with evidence;
   - amend process-local flow only when declared evidence requires it;
   - verify parent state is unchanged until explicit join/import.
3. **Second-generation Humanize-style workflow scenario**
   - combine workflow state, process topology, eval tasks, observer steering,
     human comments, and dynamic flow amendment;
   - use fixed IO rather than live LLM behavior;
   - verify the primary process responds to human/observer input through
     mailbox evidence before advancing.
4. **Source-backed merge repair scenario**
   - create deterministic parent and child branch conflict;
   - run repair from merge failure evidence;
   - inspect base/parent/child/conflict markers;
   - write proposed patch;
   - run evals;
   - block without approval for dangerous apply;
   - apply with approval and record merge-quality evidence.
5. **GitHub virtual channel scenario**
   - use fixed GitHub adapter fixtures;
   - create/comment/close issue envelopes;
   - create/comment/close PR envelopes;
   - import fixed issue and PR comments;
   - route everything through a virtual process mailbox;
   - verify missing local auth records setup guidance and no global-auth
     fallback.
6. **Promotion/deposition through skill scenario**
   - run fixed learned adapter and lesson artifacts through installable
     promotion skills/templates;
   - verify outputs, review artifacts, rollback evidence, approval gates, and
     report projection.
7. **Retention and recovery trust scenario**
   - compress or archive large evidence;
   - corrupt a ledger;
   - reconcile it while preserving damaged input;
   - verify completion audit and reports can still trace evidence lineage.
8. **Report completeness scenario**
   - generate `progress.html`, `progress.md`, and `report-data.json`;
   - verify no slide artifacts exist;
   - verify first-class report data for feature settings, derived profiles,
     process topology, process flows, amendments, mailbox links, human/GitHub
     events, observer interventions, supervisor events, evals, retention,
     recovery, deposition, merge repair, approvals, spawn/join/import, and
     completion audit.
9. **Document-code alignment scenario**
   - verify every `STATUS.md` implemented claim maps to concrete runtime files,
     installable prompts/skills where applicable, and test names;
   - verify public docs do not point to removed negotiation files or ignored
     local scratch paths;
   - verify `docs/v1-system-test-coverage.md` and
     `docs/v1-implementation-verification-guide.md` name artifacts that the
     tests actually generate.

The test suite must remain deterministic. Fake agents may run planned commands
in fixed order to mimic real agent execution.

## Workstream 5: Report And Human Review Evidence

Reports are optimized for humans only. Do not introduce duplicate LLM-facing
summaries or token-heavy report generation.

Completion requires:

- `report-data.json` contains typed sections for the new mechanisms, not only
  raw generic events;
- `progress.html` exposes process lanes, communication links, state positions,
  events, interventions, approval gates, child join/import, and artifact links;
- `progress.md` provides a compact human review index to the same evidence;
- report output includes enough stable labels or anchors for tests and human
  reviewers to inspect specific mechanisms;
- GUI adapter metadata is present without making the GUI canonical.

The visual style may stay plain in v1, but missing data is not acceptable.

## Workstream 6: Documentation And Status Alignment

After runtime and tests are strong enough, repair public docs.

Required updates:

- `STATUS.md`
  - stop overclaiming;
  - mark a feature implemented only when runtime, prompt/skill, report, and
    system-test evidence exist where applicable;
  - include test names and artifact paths for each implemented claim;
  - remove stale `TODO` framing and clearly mark superseded ideas.
- `README.md`
  - keep phase/mechanism/component architecture;
  - describe the completed v1 behavior without listing unproven internals;
  - keep Codex `/goal` as one substrate adapter.
- `docs/v1-system-test-coverage.md`
  - explain each hard system test, what it proves, and which artifacts a human
    can inspect.
- `docs/v1-implementation-verification-guide.md`
  - map design mechanisms to exact runtime files, commands, test names, and
    generated artifacts.
- `templates/.long-horizon/config-catalog.md`
  - list configurable defaults and setup-time choices for new mechanisms;
  - distinguish runtime-provided behavior from native-agent behavior.
- `CHANGELOG.md`
  - record commit/PR-sized public design and implementation changes.

No public doc should mention private scratch paths or deleted negotiation
transcripts as required evidence.

## Suggested Implementation Sequence

1. Correct the public overclaiming baseline: add the requirement matrix and
   downgrade any current `STATUS.md` claims that are not yet proven.
2. Audit each provisional module and decide whether to complete, refactor, or
   remove it.
3. Wire completed modules into process records, mailboxes, flow evidence,
   reports, and CLI commands.
4. Add or upgrade installable prompts/skills for the mechanisms.
5. Write the hard system tests with fixed fake agents and deterministic
   artifacts.
6. Strengthen reports until the tests and a human reviewer can inspect all
   required feature evidence.
7. Update README, STATUS, config catalog, coverage docs, verification guide,
   and changelog from the proven implementation.
8. Run the full test suite and a useful demo CLI flow.
9. Perform a requirement-by-requirement completion audit against
   `docs/v1-completion-upgrade-goal.md` and this document.
10. Commit only after the audit proves alignment.

## Completion Criteria

This goal is complete only when:

- every requirement in `docs/v1-completion-upgrade-goal.md` has a matrix row
  and current evidence;
- every newly added feature family has runtime behavior, agent-facing guidance,
  report projection, and hard system-test evidence where applicable;
- `STATUS.md` contains no unsupported implemented claims;
- the Python modules are integrated mechanisms, not isolated helper surfaces;
- GitHub virtual channel success and failure behavior is durable and tested;
- source-backed merge repair is tested with real branch conflict fixtures;
- promotion/deposition is exercised through skills/templates and review
  artifacts;
- report data and human views expose all required process/workflow/event
  evidence;
- public docs and code agree on behavior, names, artifacts, and limits;
- `python -m pytest -q` passes;
- a useful demo CLI flow is run or any skipped demo is justified in the final
  audit.

## Concise `/goal` Prompt

```text
Complete v1 feature implementation and doc-code alignment.

Repo: <path-to-long-horizon-repo>
Branch: feat/first-version-implementation

Strict sources of truth:
- docs/v1-completion-upgrade-goal.md
- docs/v1-feature-completion-alignment-goal.md

Read first:
- AGENTS.md
- README.md
- STATUS.md
- docs/v1-completion-upgrade-goal.md
- docs/v1-feature-completion-alignment-goal.md
- docs/v1-runtime-implementation-spec.md
- docs/v1-system-test-coverage.md
- docs/v1-implementation-verification-guide.md
- templates/.long-horizon/config-catalog.md
- .agents/skills/evolve-long-horizon-template/SKILL.md
- .agents/skills/git-commit/SKILL.md

Rules:
- Keep this as v1 completion work.
- Do not treat a Python module or CLI command as feature completion by itself.
- Complete runtime + prompt/skill + durable artifact + report + hard ST
  evidence, or downgrade the public claim.
- If blocked, exploit practical alternatives that preserve the negotiated v1
  architecture.
- Do not mention ignored scratch paths in public docs.
- Update CHANGELOG.md.

Testing bar:
- Avoid shallow helper tests.
- Add deterministic hard STs for full acceptance, Humanize-style two-loop
  fork/join, second-generation Humanize-style workflow, source-backed merge
  repair, GitHub virtual channel, promotion/deposition through skills,
  retention/recovery trust, report completeness, and doc-code alignment.

Finish:
- Run `python -m pytest -q` and a useful demo CLI flow.
- Commit cleanly and push.
- Final response: implemented capabilities, evidence, test results, remaining
  explicit gaps if any, commit hash.
```
