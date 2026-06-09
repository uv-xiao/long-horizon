# Template for long-horizon tasks

This template's purpose is to quickly prepare long-horizon agent work inside a new or an existing repository.

It should support:

1. quickly installed inside one existing repo; since the existing repo might already has it own mechanism, this template's skill must be able to inspect the repo's existing agent mechanisms and propose what should be added to merge the long-horizon mechanism into it. Briefly, this repo should provide skills to install/update the template.
2. used as a github template to create new repo.

What it should provides:

- a set of agent rules / policies / skills / hooks to construct a complete mechanism to help long-horizon agent work, especially for codex /goal.

The critical problem is: what mechanisms need to be included in this template?

Some basic requirements:

1. We should provide general features, since the features should be used for different projects and tasks;
2. We should be zero-overhead for adding features, which means if for a specific task, one features is not suitable, the features should not bring any trouble, just being disabled as it doesn't exist.
3. This template itself should have a changelog mechanism (agent rules/skills, personal used, not installed into target repos) to record what features we added.


Now, let's discuss the detailed features. We're assuming that we're working with a strong workflow, such as Codex /goal. So, our features is around "how we define the goal?". The reference works are:

- https://github.com/BBuf/kernel-pilot
- https://github.com/TongmingLAIC/AKO4ALL
- https://github.com/mit-han-lab/kernel-design-agents
- https://mp.weixin.qq.com/s/6uzb0OFDCDt4xmRcWaelaw
- https://mp.weixin.qq.com/s/pScZ_9cA-6cWUPjfcGjNyg
- https://mp.weixin.qq.com/s/S45KRGmDCCLu5GoBa7v2bQ
- Advancing Token Productivity with Agent Loops

Maintainer research logs and downloaded source material are not part of this public README. This repository's maintainer rules define where temporary evidence and review logs belong.

## System design

The template should be a small long-horizon operating system, not a flat feature bundle. Its job is to wrap a capable agent runtime, such as Codex `/goal`, with the missing engineering surfaces: goal negotiation, artifact memory, judgment gates, workspace/version control, logging, human reporting, and knowledge deposition.

The detailed v1 runtime build contract is [docs/v1-runtime-implementation-spec.md](docs/v1-runtime-implementation-spec.md). Use it when implementing the first version; this README remains the public architecture and product rationale.

The v1 prompt-first usability layer is defined in [docs/v1-template-usability-goal.md](docs/v1-template-usability-goal.md). It makes the template easier to use: target-agent analysis, install planning, task setup, goal contracts, flow assembly, execution start, live operation, completion, and deposition are guided by installable skills and phase templates, with Python commands used as validators/state tools where the selected operation mode needs them.

The core design principle is:

Generality is in the mechanism; specificity is in the judgment.

The template should provide stable mechanisms. Each task configures where judgment happens, how strict it is, which artifacts prove progress, and which agent/runtime is trusted to execute the loop.

### Design goals

1. **Install into existing repos without pretending the repo is empty.** Installation reads existing agent rules, workflow files, hooks, issue/PR practices, and available agent runtimes, then writes an installation plan for human review before applying changes.
2. **Support both planned implementation and open exploration.** A refactor task needs a closed plan; a kernel optimization task needs hard constraints plus open candidate search.
3. **Coordinate with the target agent instead of duplicating it.** If Codex `/goal` already owns persistence and continuation, this template supplies contracts, artifacts, review, versioning, and reports around it. If the target agent lacks a long-loop runtime, the template supplies a stricter prompt/hook loop.
4. **Keep optional mechanisms zero-overhead.** Reviewers, checkpoint observers, sidecar observers, dashboards, external CLIs, domain packs, sandboxes, and parallel lanes are configured per goal and disabled when not useful.
5. **Make progress inspectable.** Every long run leaves typed artifacts, logs, checkpoints, evidence, and a human-readable report.
6. **Harden judgment boundaries.** The system spends model calls where decisions matter: goal contract, plan convergence, candidate promotion, drift detection, evidence quality, completion, and merge.

## Architecture

The system has three layers:

1. **Phase layer** - the long-horizon lifecycle, from installation to workflow evolution.
2. **Mechanism layer** - reusable substrates used by many phases: artifact model, logging, version control, review, watchdogs, human I/O, memory, adapters.
3. **Component layer** - installable skills, templates, hooks, and optional dashboards that implement the mechanisms for a concrete repo and agent runtime.

This avoids overlap. For example, "draft-to-plan", "goal contract", and "user directives" are not separate features; they are parts of the **Goal Contract** phase. "checkpoint", "resume", and "commit policy" are not separate features; they are parts of the **Workspace and Version Control** mechanism.

### Operation modes

The installer and task-start phase analyze the target repository and selected
agent, cache the result in `.long-horizon/agent-capabilities.toml`, and choose
one operation mode:

- **Runtime-owned**: the target agent is weak or manual, so the template owns
  durable workflow state, transition validation, reports, comments, and
  recovery briefs.
- **Native-agent**: the target agent already has loop orchestration, hooks,
  subagents, review, stop gates, or process/session controls. The template
  installs prompts, policies, validators, and evidence/report surfaces without
  duplicating the native loop.
- **Hybrid**: the target agent owns some orchestration while the template owns
  durable contracts, flow snapshots, evidence gates, reports, git/worktree
  handling, or human interaction routing.

This decision is an artifact, not doctrine. Re-run capability analysis or
override `agent.operation_mode` when a repo/task needs different behavior.

### Prompt-first usage flow

1. Analyze the target agent and repository:
   `python -m long_horizon capabilities analyze --root . --target-agent auto`
2. Review `.long-horizon/agent-capabilities.md`,
   `.long-horizon/decisions/operation-mode.md`, and
   `.long-horizon/install-plan.md`.
3. Install the mode-aware prompt/runtime surface:
   `python -m long_horizon install --target . --apply`.
4. Start a task from the human request:
   `python -m long_horizon task setup --root . --request "<request>"`.
5. Follow the installed phase skills in `.agents/skills/`: create the goal
   contract, assemble the flow, start execution, operate checkpoints/fork-join
   or recovery, and complete/deposit reusable knowledge.

The installed prompts under `.agents/templates/long-horizon/` are the
user-facing workflow. Python commands are validator and state tools used by
those prompts when the selected operation mode needs them.

## Phase layer

### Phase 0: Installation and capability negotiation

Purpose: install the long-horizon mechanism into a repo without damaging existing agent practice.

Inputs:

- Target repository path.
- Existing agent files such as `AGENTS.md`, `CLAUDE.md`, `.agents/`, `.claude/`, hooks, issue/PR docs, CI, and local scripts.
- Target agent runtime: Codex `/goal`, Codex without `/goal`, Claude Code, Humanize, oh-my-pi, or another runner.
- Human interaction preferences: plain Markdown, CLI prompts, Feishu CLI, GitHub issues/PR comments, a Perfetto-like local report timeline, or a small local dashboard.

Outputs:

- `.long-horizon/install-plan.md`: what will be added, changed, extended, or left alone.
- `.long-horizon/agent-capabilities.md`: what the selected agent already provides, such as goal persistence, tool permissions, hooks, subagents, review, or stop conditions.
- `.long-horizon/config.toml`: selected mechanisms, directories, review policy, logging policy, worktree root, sandbox mode, human notification channel, and disabled options.
- `.long-horizon/config-catalog.md`: every configurable policy, current default, allowed alternatives, storage location, validation rule, and helper skill or command for changing it.
- Installed skills/templates/hooks only after human review of the install plan.

Rules:

- The installer should not blindly "avoid overwrite"; it should classify existing rules, propose merge/replace/extend choices, and ask for human approval when the local policy is ambiguous.
- Defaults are not doctrine. Installation and goal setup can override workspace, branch, snapshot, merge, commit, sandbox, review, reporting, evaluator, and adapter policies when the target repo or task needs different behavior.
- The configuration catalog should be complete enough that an agent can inspect it, propose a safe policy patch, run validators, and record a decision artifact without rediscovering hidden assumptions.
- Active-run policy changes are side artifacts by default and require workflow transitions only when they alter goal constraints, human gates, safety boundaries, acceptance evidence, or branch/process topology.
- Active-run policy changes do not automatically mutate already-spawned children; parents must explicitly push a child update, ask for brief adoption, or respawn the child.
- The installer creates durable directories for long-horizon memory and logs. Default:

```text
.long-horizon/
  config.toml
  config-catalog.md
  install-plan.md
  agent-capabilities.md
  goals/
  logs/
  memory/
  reports/
  workflow/
```

Evidence:

- `AKO4ALL/SKILL.md` copies scaffolding only when missing, which supports safe installation.
- `kernel-design-agents/CLAUDE.md` separates reusable workflow mechanics from task-specific artifacts.
- Humanize H2 uses manifests to declare agent tools, artifact schemas, script allowlists, human input, and views, which is the right shape for capability negotiation.

### Phase 1: Goal contract and judgment setup

Purpose: convert a human request into a durable contract that distinguishes hard constraints from open exploration.

The goal contract is not the same as an execution plan.

- **Goal**: stable target and success semantics.
- **Constraints**: what must not change, including APIs, safety boundaries, datasets, target hardware, budgets, files, branches, dependency policy, and non-goals.
- **Open search space**: what the agent may explore, such as candidate algorithms, kernel implementations, optimization strategies, alternative architectures, or unknown root causes.
- **Plan**: current route through the search space. It can evolve, but every change must be logged against the stable goal.

Required contract fields:

```text
Goal:
  objective
  why this matters
  expected deliverables

Constraints:
  hard requirements
  non-goals
  frozen files or APIs
  safety/compliance boundaries
  dependency and environment policy
  token/time/budget limits

Open search:
  candidate dimensions
  allowed exploration methods
  when to broaden search
  when to ask human

Verification:
  correctness checks
  evaluation metrics
  evidence artifacts
  promotion criteria
  completion criteria

Judgment policy:
  review mode
  watchdog policy
  human intervention mode
  version granularity
```

Task-understanding prompt:

- `K`: kernel, code, or system semantics. What is the implementation/callsite contract?
- `R`: reference and requirements. What is the correctness oracle, validation path, and invariant set?
- `W`: workload and world. What inputs, benchmark, environment, user journey, or operating condition defines success?

`K/R/W` is a default reasoning scaffold, not a fixed domain model. A skill may replace it with another prompt for non-technical tasks, but it should preserve the same intent: semantics, requirements, and workload.

Judgment setup:

- Planned implementation tasks use a plan-convergence gate.
- Open exploration tasks use a goal-contract gate plus search policy. The plan may start as a candidate-search protocol rather than a fixed sequence.
- Human review is strongest before the first long loop. Humanize calls this "Begin with the End in Mind"; this template should generalize it beyond implementation plans.

Evidence:

- `kernel-design-agents/docs/agent-flow.md` defines objective, inputs/outputs, correctness, constraints, validation, evaluation, and promotion criteria.
- `kernel-pilot` prompts hard-code workload shapes and correctness oracles but allow exploration within candidate kernels.
- Humanize workflow notes say the plan must make goal, acceptance criteria, and evidence falsifiable before the loop starts.
- Humanize H2's plan-generation flow models plan generation as relevance check, first-pass analysis, candidate plan, convergence review, human decision, and final plan.

### Phase 2: Flow assembly and workspace provisioning

Purpose: assemble a concrete workflow and isolate its execution.

The workflow specification should be declarative enough to inspect and adapt, even if the first version is implemented as Markdown plus skills rather than a full runtime. Humanize H2's cartridge model is the strongest reference shape:

- manifest: allowed agent tools, script allowlist, artifact schemas, human input, views;
- boards: mutable loop state such as goal tracker and loop status;
- artifacts: immutable outputs such as plan, round summary, review verdict, benchmark result;
- flow: bounded loops, branches, checks, human gates, parallel lanes;
- views: human-facing status projection.

For this template, call this a **Goal Flow**. A Goal Flow can be represented as Markdown/TOML/JSONL initially, with an optional H2-like HTML cartridge later.

Workspace policy:

- Each goal gets a task-owned workspace.
- Default worktree root is configured during installation, for example `../<repo>-long-horizon-worktrees/`.
- Each candidate lane that may edit repository files gets its own branch/worktree.
- Branchless child processes are allowed only for read-only research, inspection, reporting, or evaluation tasks, and that mode must be recorded in process metadata.
- Parent wait/join gates are declared in the Goal Flow for v1. Selectors are all children, explicit process ids, and lane role selectors. Conditions are `completed`, `artifact_present`, `checks_passed`, `cancelled_or_rejected`, `timed_out`, `budget_exhausted`, or conjunctions such as `artifact_present + checks_passed`; quorum counts selected children satisfying the declared condition set. Non-success terminal states count only when the flow explicitly allows them.
- A pinned review base is created before the loop starts.
- Sandbox policy is declared before execution:
  - no sandbox: trusted local repo, fast iteration;
  - command allowlist: normal engineering work with possible destructive commands;
  - container/remote sandbox: dependency-heavy, GPU, untrusted code, or benchmark tasks;
  - human approval required: secrets, auth, infra, production, legal/compliance.

Version policy:

- **Commit** when a coherent step changes code, state, or evidence enough that rollback should be possible.
- **Candidate commit** when an explored implementation/evaluation point must be compared.
- **Checkpoint tag/branch** when a loop milestone, review pass, or budget boundary is reached.
- **PR** when the work becomes reviewable by humans or when a candidate should enter repository review.
- **Merge** only after completion audit, required CI/evaluation, source-lineage checks, and any configured human review pass.

Evidence:

- `kernel-pilot/scripts/launch_kda_kernel_task.sh` creates branch, worktree, and pinned review base per run.
- `kernel-pilot/docs/ghostty_claude_code_workflow.md` warns against multiple RLCR sessions in one checkout.
- Humanize H2's `rlcr` cartridge declares `git.statusClean`, `git.detectBase`, nested loops, goal tracker board, and code review branches.

### Phase 3: Execution loop

Purpose: advance the goal through bounded, reviewable steps.

Default loop shape:

1. Builder executes the next step or candidate.
2. Builder emits a typed round summary with changed files, evidence, decisions, next step, and memory delta.
3. Mechanical checks compare claims to disk, logs, and policy.
4. Reviewer/critic judges goal progress, evidence quality, drift, and required follow-up.
5. Branch:
   - continue/revise;
   - broaden search;
   - fork candidate lane;
   - queue side issue;
   - ask human;
   - stop as blocked/no-go;
   - enter final audit.

Candidate exploration:

- Candidate generation belongs in the loop body, not only in completion criteria.
- Exploration lanes are used when candidates are independent enough to avoid boundary tax.
- Each lane inherits the same goal contract and writes separate candidate artifacts.
- A coordinator ranks lanes by evidence density, correctness, risk, and target metric.
- Failed candidates are first-class evidence, not waste.

Review modes configured in Phase 1:

- **Weak review**: same-context self-review or Codex `/goal` internal review.
- **Strong review**: fresh independent reviewer agent, ideally different model family.
- **Static review**: every round, every N rounds, or every milestone.
- **Dynamic review**: triggered by drift score, repeated failure, evidence gap, frozen-file touch, budget threshold, or candidate promotion.
- **Full alignment check**: heavier audit against original goal and constraints every N rounds or before promotion.

Watchdog policy:

- Every step declares expected output.
- Every step gets a goal-alignment score.
- Repeated failure on the same step triggers retry cap and rollback.
- Token/time overrun triggers checkpoint and human report.
- Plan modifications, rollback count, drift score, and repeated-review findings are logged as metrics.

Evidence:

- Humanize workflow notes say review decides whether the loop still advances the main goal, not whether a diff merely looks plausible.
- Humanize workflow notes recommend full alignment checks every N rounds.
- The article "如何避免Agent在长任务里跑偏" recommends per-step output binding, goal scoring, critic checks, retry caps, token interrupts, and checkpoint rollback.
- Humanize H2's idea-generation flow uses parallel exploration proposals and synthesis, which is a useful reference for open candidate search.

### Phase 4: Evaluation, promotion, and completion

Purpose: decide whether a candidate should become the new baseline, a PR, a merge, a no-go, or a follow-up.

Evaluation is a family of adapters, not a single performance feature.

Adapter examples:

- code correctness: tests, type checks, lint, static analysis;
- benchmark: fair workload, baseline, variance/noise threshold, hardware state;
- profile: root-cause evidence, NCU/profiler digest, bottleneck classification;
- product: screenshot, UX trace, acceptance walkthrough;
- research: reproduced table, ablation, citation evidence;
- operational: incident replay, capacity estimate, rollback test.

Promotion rules:

- A candidate must satisfy hard constraints first.
- It must have direct evidence for the target metric or deliverable.
- Evidence must be recent enough and collected under the configured environment.
- Accuracy/correctness evidence is tracked separately from speed/cost evidence.
- Source lineage and anti-cheat checks must pass.
- A no-go is valid only when attempts, evidence, blockers, and remaining search space are documented.

Completion audit:

- Re-read the original goal contract.
- Verify every acceptance criterion against a concrete artifact.
- Verify every non-goal and frozen constraint was respected.
- Confirm side issues are queued rather than silently dropped.
- Confirm the final version is the intended version, not merely the latest worktree state.
- Write final report and PR/merge recommendation.

Evidence:

- `kernel-design-agents/docs/agent-flow.md` promotes only candidates that satisfy the task contract and have evidence.
- `SGLang SOTA Humanize Loop...txt` shows benchmark/profile/patch/retest and separates benchmark from accuracy evidence.
- `AKO4ALL/SKILL.md` requires documented directions before stopping as exhausted.
- `kernel-pilot` interface files require final signatures, dispatch table, fallback cases, tolerance methodology, benchmark command, and source lineage.

### Phase 5: Reporting, memory, and workflow evolution

Purpose: turn a long run into reusable team knowledge and improve the template itself.

Reporting:

- Human reports are generated from artifacts, not chat memory.
- Markdown report and one static HTML Perfetto-like timeline are required.
- Optional presentation adapters:
  - CLI report for terminal;
  - Feishu/GitHub notification;
  - local dashboard or H2-style view for live workflow state.

Memory:

- Record anti-patterns, failure causes, shortcuts, and fast paths.
- Use typed lesson entries rather than dumping all notes into context.
- Route memory by task topic/framework/subsystem.
- Track which sources were read to avoid repeated reading loops.
- Backends may be simple Markdown first, then a self-hosted LLM wiki, PageIndex, or another searchable memory system when scale requires it.

Workflow evolution:

- The template has its own `CHANGELOG.md`.
- Loop exits may emit methodology notes: what judgment failed, which guard caught it, what should change.
- Template-local rules/skills/hooks evolve from observed failures, not abstract feature wishlists.

Evidence:

- Humanize BitLesson keeps `.humanize/bitlesson.md`, selects relevant lessons, and validates round summary deltas.
- Humanize workflow notes say memory decays if not machine-checked and warn that dumping all lessons into context is worse than none.
- `月烧 6300 刀才明白...txt` treats `.humanize/rlcr/` as team trust evidence and proposes AC coverage, RLCR convergence rounds, BitLesson reuse, and finding severity distribution as better signals than LOC.
- Humanize workflow notes say serious workflows improve their own workflow through process reports and methodology issues.

## Mechanism layer

### M1. Agent substrate adapter

The adapter records what the target agent already provides and what the template must provide.

Examples:

| Target agent | Use built-in | Template supplies |
| --- | --- | --- |
| Codex `/goal` | Persistent objective, continuation loop, goal completion accounting | Goal contract artifacts, review policy, logging, version/checkpoint policy, human reports |
| Codex without `/goal` | Tool execution and code editing | Explicit loop prompts, state files, watchdog, resume instructions |
| Humanize | RLCR loop, review, hooks, monitor, BitLesson | Goal-contract generalization for open exploration, repo install/update plan, adapter-specific reports |
| Claude Code | strong builder, subagents | Reviewer bridge, durable artifacts, checkpoint/version policy |
| oh-my-pi or other runner | runner-specific automation | Capability manifest and missing mechanisms |

### M2. Artifact and board model

Use Humanize H2 terminology as the reference model:

- **Artifact**: immutable schema-tagged output delivered once, such as goal contract, plan, round summary, review verdict, benchmark result.
- **Task board**: mutable workflow state updated by transition tooling, such as goal tracker, loop status, and candidate scoreboard.
- **Observer board**: mutable meta-progress state updated by watchdog/critic tooling, such as drift score, retry pressure, evidence gaps, budget pressure, and run-health alerts.

This can start as Markdown/TOML/JSONL files:

```text
.long-horizon/goals/<goal-id>/
  contract.md
  flow.toml
  boards/
    goal-tracker.toml
    loop-status.toml
    candidate-scoreboard.toml
  observer/
    run-health.toml
    watchdog.toml
    evidence-gaps.toml
  artifacts/
    plans/
    summaries/
    reviews/
    evaluations/
    reports/
```

### M3. Unified logging mechanism

Logging is a substrate, not a monolithic feature.

Every component declares:

- log type: decision, plan change, candidate, evaluation, review, command, error, memory, human interaction;
- level: trace, info, warning, blocking, audit;
- storage: summary file, JSONL ledger, raw artifact directory, external issue/PR;
- presentation: hidden, report summary, dashboard, human notification.

Default hierarchy:

```text
logs/
  timeline.md              # high-level human-readable run history
  decisions.md             # why choices changed
  commands.jsonl           # command/eval provenance
  candidates.jsonl         # candidate lineage and status
  evaluations.jsonl        # metrics and evidence pointers
  reviews.jsonl            # verdicts and severity
  raw/                     # tool outputs, profiles, screenshots
```

### M4. Workspace, version, checkpoint, and sandbox

One mechanism owns isolation and rollback:

- worktree root and branch naming;
- pinned review base;
- candidate lane branches;
- commit/PR/merge granularity;
- checkpoint tags;
- rollback target;
- sandbox level and command allowlist.

### M5. Judgment policy

One mechanism owns review, critic, watchdog, and human gates:

- weak/strong review;
- static/dynamic review cadence;
- full alignment checks;
- critic triggers;
- retry budget;
- stop conditions;
- human modes: watchtower, checkpoint, co-pilot, handoff.

Watchdog and meta-progress use a separate observer board. Task workflow boards answer where the work is in the flow; observer boards answer whether the run is healthy, drifting, looping, under-evidenced, over budget, or repeatedly failing. Reports render both, but the transition tool remains the only owner of task workflow boards.

V1 supports both observer modes:

- **Checkpoint observer runs**: bounded observer processes triggered at configured checkpoints, transitions, reports, or human-requested audits.
- **Long-running observer sidecars**: tmux-backed observer processes that watch task processes during high-risk or long-running work.

Both modes use explicit observe grants and steer grants. Observers usually attach to a task or parent process workspace/state root rather than getting a separate workspace, but they may observe multiple granted target processes across workspaces. Dedicated observer workspaces are optional for heavy tools, isolation, or multi-workspace monitoring. Observers may read granted state files, ledgers, artifacts, reports, process metadata, git status, and adapter-supported tmux/thread capture. They write observer boards as latest summaries, with append-only watchdog/intervention events as source of truth. Captured LLM text is treated as a signal until verified against files, artifacts, checks, or process metadata.

Observers may steer task processes only through granted input channels such as tmux input, agent thread messages, or regenerated briefs. Every steering action must be recorded as an append-only intervention before or atomically with delivery; observers still cannot mutate task boards or advance workflow state.

Humanize's modes map well:

- **watchtower**: human reads dashboard only;
- **checkpoint**: human signs off at milestones;
- **co-pilot**: human reviews every round;
- **handoff**: human takes over on specific triggers.

### M6. Evaluator and evidence adapters

Evaluators are task adapters. A performance adapter can freeze a fair baseline and run profiles, but that is only one adapter type. The same mechanism supports tests, screenshots, incident replay, research reproduction, and static analysis.

### M7. Knowledge and memory router

Memory has two flows:

- retrieval before work: choose relevant lessons/docs/source notes;
- deposition after work: record new pitfalls, recipes, shortcuts, anti-patterns, and source-read markers.

This must be routed. A kernel task should not load every serving incident lesson; a frontend task should not load NCU notes.

### M8. Reporter and human interaction

Reporter owns presentation. Other components log artifacts; reporter renders them.

Required:

- Markdown progress report.
- Final report.
- Main timeline with compact observer intervention markers.
- Dedicated observer intervention lane/table with target process, trigger evidence, steering message, delivery result, and acknowledgement state.
- Static HTML Perfetto-like progress timeline for human inspection.

Optional:

- CLI notification.
- Feishu/GitHub update.
- local dashboard or hosted view.
- configured reporter analysis on the timeline for human review.

The reporter does not own canonical task state or append-only event history. It may, when configured, write derived timeline annotations, summaries, suspected causal links, risk notes, and review questions beside the source-backed timeline. Those annotations are reporter-authored analysis for humans to accept, reject, or supersede; they do not rewrite ledgers, task boards, observer boards, or workflow state.

## Component layer

Initial installable modules:

```text
skills/
  install-long-horizon/       # repo inspection, capability negotiation, install/update plan
  configure-long-horizon/     # inspect and modify installed policy defaults
  update-long-horizon-policy/ # active-run policy patch with validation and decision artifact
  goal-contract/              # goal review, constraint/open-search negotiation, K/R/W prompt
  assemble-flow/              # creates flow.toml or H2-style cartridge from selected mechanisms
  observe-workflow/           # checkpoint and sidecar observer processes
  run-loop/                   # fallback loop for agents without native long-goal runtime
  review-critic/              # weak/strong review prompts and full-alignment checks
  audit-completion/           # final requirement-by-requirement audit
  report-progress/            # human reports and notifications
  memory-curator/             # lesson routing and deposition

templates/
  config.toml
  config-catalog.md
  install-plan.md
  agent-capabilities.md
  goal/contract.md
  goal/flow.toml
  goal/boards/*.toml
  goal/observer/*.toml
  goal/logs/*.md
  reports/progress.md
  reports/final.md
  team/boundaries.md
  memory/lesson.md

hooks/
  command-allowlist
  frozen-file-guard
  summary-contract-check
  evidence-claim-check
  drift-score-check
  budget-check
  git-clean-check

CHANGELOG.md
```

Optional future module:

```text
workflow/
  cartridges/                 # H2-style HTML workflows when a runtime exists
  schemas/                    # artifact and board schemas
  views/                      # local dashboard/report views
```

## Canonical flows

### Planned implementation flow

Use for refactors, feature implementation, migrations, and bug fixes where the end state is mostly known.

```text
install -> goal contract -> plan convergence -> workspace -> build/review loop
-> code review -> completion audit -> PR/merge -> memory/report
```

### Open exploration flow

Use for kernel optimization, model serving SOTA chasing, research engineering, or root-cause search.

```text
install -> goal contract with hard constraints + open search space
-> fair baseline/evidence adapter -> candidate generation
-> parallel or serial candidate lanes -> rank/promote/no-go
-> final verification on original workload -> memory/report
```

### Incident or maintenance flow

Use for production bugs, flaky failures, and complex debugging.

```text
install -> goal contract with safety boundaries -> reproduce/evidence gate
-> hypothesis lanes -> patch/review -> regression proof
-> completion audit -> follow-up side issues -> memory/report
```

## Why this structure is better than the flat list

- Human interaction is not a feature; it is part of installation, judgment policy, and reporting.
- Goal contract, plan draft, K/R/W, and user directives are one phase: goal and judgment setup.
- Workspace, checkpoints, resume, versioning, sandbox, commits, PRs, and merge policy are one mechanism.
- Logging is a substrate used by planner, evaluator, reviewer, memory, and reporter.
- Review, watchdog, critic, and completion audit are one judgment policy with different strictness and cadence.
- Fair benchmark/profile is not a universal phase; it is one evaluator adapter used by performance tasks.
- Team trust metrics are report/memory outputs, not a standalone runtime mechanism.
- Parallel agents belong in candidate exploration and can use the workspace/version mechanism.

## Evidence map

| Design element | Evidence |
| --- | --- |
| Human remains architect; goal/AC/evidence first | Humanize workflow notes, Humanize usage docs, "月烧 6300 刀才明白..." |
| Build/review loop and full code review | Humanize README, Humanize H2 RLCR flow |
| H2 artifact/board/manifest/flow/view model | Humanize2 article, Humanize H2 workflow model |
| Separate task workspaces and pinned review base | `kernel-pilot/README.md`, `scripts/launch_kda_kernel_task.sh` |
| Goal contracts and evidence records | `kernel-design-agents/docs/agent-flow.md`, `prompts/basic-flow.md` |
| Open exploration with candidate ledgers | `kernel-pilot` task folders, `Humanize 带来的Codex使用范式变化...txt` |
| Fair baseline/profile/retest adapter | `SGLang SOTA Humanize Loop...txt` |
| Step watchdog and drift metrics | "如何避免Agent在长任务里跑偏", Humanize workflow mainline drift sections |
| BitLesson and routed memory | Humanize `docs/bitlesson.md`, `月烧 6300...txt` |
| Agent capability adaptation | Humanize H2 manifests, Codex `/goal` comments in this README |

## Maintainer evolution

This repository has maintainer-only rules and skills for evolving the template itself. They keep temporary evidence, review logs, and private research paths out of public template documentation while preserving the reasoning needed to improve the design.
