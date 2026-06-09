# V1 Template Usability And Agent-Substrate Goal

This document defines a completion goal for the v1 template. The purpose is to
make the long-horizon template usable as a guided phase system, not only as a
set of Python scripts.

V1 completion note: `docs/v1-completion-upgrade-goal.md` supersedes the older
operation-mode wording in this document where they differ. Runtime-owned,
native-agent, and hybrid are now compatibility/profile labels derived from
small feature settings and a responsibility map.

## Problem

The current implementation proves durable state, workflow validation, logging,
reports, comments, git worktrees, and adapter paths. It is still not friendly
enough for real users because it exposes mechanisms mostly as commands and
runtime files.

Long-horizon work needs installable prompts, skills, and phase templates that
tell an agent or human what to do before, during, and after the runtime commands.
The template must also adapt to the target agent. Some agents need the template
to provide a stable runtime. Other agents already have orchestration, hooks,
subagents, stop gates, or loop management, so this template should mainly
provide goal contracts, prompts, validation artifacts, policy, and reporting
while enabling the agent's native features.

## Reference Lessons From Humanize-Style Templates

Humanize-style workflows are not just scripts. They provide command templates
with:

- argument hints and allowed tool boundaries;
- hard constraints such as planning-only phases;
- sequential phase lists that agents must follow;
- config loading and merge semantics;
- IO validators before the main work begins;
- external or secondary-agent critique before plan acceptance;
- plan compliance checks before starting an implementation loop;
- user understanding checks before high-risk execution;
- goal tracker and acceptance-criteria ledgers;
- stop hooks and review gates that enforce loop semantics;
- memory deposition prompts such as lesson selection and delta validation.

The long-horizon template should learn this shape, but generalize it beyond one
agent/runtime. Scripts remain useful as validators and state tools; prompts and
skills must become the user-facing workflow.

## Objective

Implement a phase/template layer that makes a target repository ready for a
specific long-horizon task by:

1. analyzing the target repository and target agent substrate;
2. choosing runtime-owned, native-agent, or hybrid operation mode;
3. installing or updating the right agent-facing rules, skills, prompts, hooks,
   and runtime files;
4. guiding users through setup, goal-contract creation, flow assembly, process
   start, live supervision, review, completion, and knowledge deposition;
5. caching capability analysis so future tasks do not repeat full discovery;
6. keeping all decisions inspectable and configurable.

## Key Design Principle

The template should decide how much runtime to provide based on target-agent
capabilities.

```text
capability analysis + task needs + human policy
  -> operation mode
  -> installed skills/templates/hooks/runtime surface
```

The decision is not hard-coded globally. It is made during installation or task
setup, recorded as evidence, and can be overridden by configuration.

## Operation Modes

### Runtime-Owned Mode

Use when the target agent lacks reliable long-loop orchestration or process
management.

The template provides:

- `.long-horizon/` runtime state;
- Python validators and transition tooling;
- process supervisor or adapter-backed handles when implemented;
- generated agent briefs;
- observer/report/comment mechanisms;
- explicit restart/recovery guidance.

### Native-Agent Mode

Use when the target agent already provides loop orchestration, hooks, stop
gates, subagents, review, process/session management, or a comparable runtime.

The template provides:

- goal-contract prompts;
- phase command templates;
- validators and artifact schemas;
- policy overlays;
- native feature enablement instructions or hooks;
- report/comment surfaces when useful;
- minimal runtime state only for evidence and compatibility.

In this mode the template should not compete with the target agent's own loop.
It should make the native features stricter, better configured, and more
auditable.

### Hybrid Mode

Use when the target agent handles some orchestration but the template still
needs durable workflow state, reporting, git/worktree handling, or human
interaction routing.

Examples:

- target agent owns subagent dispatch, template owns goal contract and evidence
  gates;
- target agent owns stop hooks, template owns process/worktree state;
- target agent owns UI, template owns `report-data.json` and ledgers.

## Required Phases

### Phase 0: Target Analysis

Add a skill that inspects the target repository and selected agent substrate.

The skill must inspect, when present:

- repo-level instructions such as `AGENTS.md`, `CLAUDE.md`, `.agents/`,
  `.claude/`, `.cursor/`, or equivalent agent directories;
- existing workflow docs, issue/PR conventions, CI, scripts, hooks, and local
  config;
- available target-agent features such as goal persistence, hooks, subagents,
  review commands, stop conditions, native process/session management, and local
  GUI/report support;
- local auth and adapter prerequisites when GitHub or other external systems
  are requested.

Outputs:

- `.long-horizon/agent-capabilities.toml`: structured capability cache;
- `.long-horizon/agent-capabilities.md`: human-readable analysis;
- `.long-horizon/install-plan.md`: proposed install/update plan;
- `.long-horizon/decisions/operation-mode.md`: selected mode, alternatives,
  risks, and override knobs.

The skill should reuse cached analysis when it is fresh and the target agent,
repo instructions, or relevant config files have not changed.

### Phase 1: Installation And Merge Plan

Installation must be a prompt-guided plan before it is a write operation.

The installer should propose:

- which skills/templates/hooks/rules will be added;
- which existing files will be extended;
- which native agent features should be enabled instead of duplicated;
- which runtime files are required for the selected operation mode;
- what is disabled and why.

Human approval is required before modifying existing agent-facing files when
the merge is ambiguous.

### Phase 2: Task Setup

Add a task-start skill/template that turns a human request into a concrete
long-horizon setup.

It should produce:

- task profile: planned implementation, open exploration, benchmark loop,
  research, debugging, review-only, or maintenance;
- operation-mode confirmation or override;
- selected phase templates;
- required artifacts and gates;
- expected process topology;
- human notification/comment policy.

### Phase 3: Goal Contract

Provide a prompt template for goal-contract creation. It must separate:

- stable objective;
- hard constraints and non-goals;
- open search space;
- acceptance criteria;
- evidence artifacts;
- evaluator/check commands;
- human decision points;
- version/control policy.

The template should include a review pass that challenges missing acceptance
criteria, vague deliverables, weak evidence, and unsafe assumptions before the
execution flow starts.

### Phase 4: Flow Assembly

Provide templates to assemble a workflow/flow from selected mechanisms.

The user-facing output should be readable Markdown plus structured TOML/JSON
where needed. It must describe:

- phases and states;
- allowed transitions;
- gates and evidence;
- parent/child/fork/join topology;
- observer and reporter roles;
- native-agent responsibilities versus template responsibilities.

### Phase 5: Execution Start

Provide a prompt/skill to start execution in the selected mode.

Runtime-owned mode starts or instructs the user to start template-supervised
processes. Native-agent mode enables or verifies the target agent's native loop
and gives it the generated brief. Hybrid mode does both only where needed.

### Phase 6: Live Operation

Provide prompt templates for:

- checkpoint review;
- observer/watchdog intervention;
- fork exploration start;
- join and candidate selection;
- human comment handling;
- recovery after agent/session exit;
- policy change during an active run.

These prompts should call validators and runtime commands only where the
selected operation mode needs them.

### Phase 7: Completion And Deposition

Provide templates for:

- completion audit;
- code/PR review;
- adapter/skill promotion review;
- artifact retention sidecar review;
- methodology/lesson deposition;
- template evolution feedback.

Adapter and skill promotion should be modeled as a process-ending review step,
not as an always-on hard-coded mechanism.

## Required Installable Components

Add or update installable skills under `.agents/skills/`:

- `analyze-target-agent/`: detect and cache agent/repo capabilities.
- `install-long-horizon/`: produce and apply mode-aware install plans.
- `start-long-horizon-task/`: create task setup, operation mode, and goal
  contract scaffolding.
- `create-goal-contract/`: generate and review the durable goal contract.
- `assemble-goal-flow/`: build flow files and human-readable phase plans.
- `start-execution/`: start runtime-owned/native/hybrid execution.
- `operate-long-horizon-process/`: handle checkpoints, fork/join, recovery,
  observer interventions, and policy changes.
- `complete-and-deposit/`: audit completion and handle memory/skill/adapter
  deposition.

Add prompt templates under `templates/prompts/` or an equivalent installable
template directory:

- target analysis;
- install plan;
- task setup;
- goal contract;
- flow assembly;
- execution brief;
- observer intervention;
- join decision;
- completion audit;
- deposition review.

The templates should be concrete enough that a capable agent can follow them
without already knowing this repository's implementation internals.

## Runtime Changes Needed

The v1 Python runtime remains useful, but the completed v1 usability layer must
expose it as one possible substrate.

Required changes:

- config supports `operation_mode = "runtime-owned" | "native-agent" |
  "hybrid"`;
- agent capability cache can be read by installer and task-start skills;
- generated briefs name the selected mode and the target-agent responsibilities;
- install plan lists native-agent features to enable, not only template files
  to write;
- reports include operation mode and capability-analysis provenance.

## Acceptance Criteria

1. A new target repo can run the install skill and receive an install plan that
   explains whether the template will use runtime-owned, native-agent, or hybrid
   mode.
2. Capability analysis is cached and reused unless relevant repo/agent inputs
   change.
3. A Codex `/goal` target is configured as an adapter, not assumed to be the
   only execution model.
4. A target agent with native orchestration can be configured in native-agent or
   hybrid mode without duplicating its loop.
5. The template installs prompt/skill phase templates that guide a user through
   setup and execution without requiring them to manually infer command order
   from scripts.
6. Goal-contract and flow-assembly prompts include explicit review/challenge
   phases before execution starts.
7. Runtime commands remain available and tested, but each user-facing phase says
   when and why to call them.
8. Post-run adapter/skill promotion, artifact retention, merge-conflict repair,
   and ledger repair are represented as processes or workflow steps in prompts,
   not merely as hard-coded backlog items.
9. Documentation explains how to choose and override operation mode.
10. Tests cover at least two target-agent profiles:
    - weak/no-native-orchestration agent -> runtime-owned mode;
    - strong/native-orchestration agent -> native-agent or hybrid mode.

## Suggested Tests

Use focused system tests, not shallow prompt snapshot churn.

- Install into a fake repo with no agent features and assert runtime-owned mode,
  full runtime artifacts, and complete phase templates.
- Install into a fake repo with native hooks/subagents/review features and
  assert native-agent or hybrid mode, no duplicate loop, and explicit feature
  enablement.
- Change an input that affects capability analysis and assert the cache is
  invalidated.
- Start a task from a human request and assert goal-contract, flow, execution
  brief, and operation-mode decision artifacts are generated.
- Verify prompt templates contain hard constraints, sequential phases, allowed
  writes/tools, review gates, and validator calls where appropriate.

## Non-Goals

- Do not replace the v1 runtime.
- Do not implement a full GUI in this goal.
- Do not bind the template to one agent vendor.
- Do not require every target agent to use the Python runtime.
- Do not force a single workflow shape for all long-horizon tasks.

## Implementation Order

1. Add capability-analysis data model and cache invalidation rules.
2. Add the target-agent analysis skill and install-plan prompt.
3. Add operation-mode config and docs.
4. Add phase prompt templates.
5. Add task-start, goal-contract, and flow-assembly skills.
6. Update installer to choose install surface by operation mode.
7. Add execution-start and live-operation skills.
8. Add completion/deposition skill.
9. Add system tests for weak-agent and strong-agent profiles.
10. Update README, STATUS, changelog, and verification docs.
