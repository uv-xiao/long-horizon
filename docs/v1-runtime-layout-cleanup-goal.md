# V1 Runtime Layout Cleanup Goal

## Problem

The current v1 runtime still mixes several ownership scopes under
`.long-horizon/`:

- repo-install state such as config, capability analysis, install plans, and
  operation-mode decisions;
- task-intake scaffolding under `.long-horizon/tasks/`;
- goal/run execution state under `.long-horizon/goals/<goal>/runs/<run>/`;
- root-level `logs/`, `reports/`, `artifacts/`, `flows/`, and `decisions/`
  created during install or target analysis.

This makes eval output hard to inspect and weakens the process model. Execution
evidence should be owned by a goal, run, and process. Root-level runtime state
should be small, stable, and not look like task execution residue.

## Target Layout

The cleaned v1 layout must use this ownership model:

```text
.long-horizon/
  config.toml
  config-catalog.md
  agent-profile.toml
  agent-profile.md
  goals/
    <goal-id>/
      contract.md
      flow.toml
      policy.snapshot.toml
      setup/
        intake.md
        intake.toml
        execution-brief.md
        goal-contract.scaffold.md
      decisions/
        operation-mode.md
      runs/
        <run-id>/
          run.toml
          eval-manifest.json
          eval-result.json
          boards/
          logs/
          artifacts/
          reports/
          observer/
          processes/
            <process-id>/
              process.toml
              flow.toml
              flow-amendments.jsonl
              mailbox/
              logs/
```

Root-level `.long-horizon/logs/`, `.long-horizon/reports/`,
`.long-horizon/artifacts/`, `.long-horizon/flows/`, `.long-horizon/decisions/`,
and `.long-horizon/tasks/` should not be created by normal v1 install or task
execution.

## Design Decisions

- The eval directory itself is the target repo. Do not create a nested
  `target-repo` wrapper.
- Execution logs for launched eval processes must live in
  `goals/<goal>/runs/<run>/processes/<process>/logs/`.
- Goal setup artifacts should live under `goals/<goal>/setup/`, not a separate
  root-level `tasks/<task-id>/` tree.
- The default reusable flow should be copied into the goal as
  `goals/<goal>/flow.toml`; a root-level `flows/` directory is unnecessary for
  v1 unless future multi-goal flow libraries need it.
- Capability analysis and config currently overlap. Replace
  `agent-capabilities.*` with `agent-profile.*`, whose purpose is target-agent
  compatibility analysis. Keep `config.toml` as the effective operator-chosen
  runtime configuration. The profile may propose config defaults, but config is
  authoritative.
- Operation-mode decisions belong to the goal setup context once a task/goal is
  initialized. Install may produce a plan, but not a root-level decision log.

## Implementation Requirements

1. Update path helpers so every execution artifact can be addressed through
   goal/run/process ownership.
2. Update install so it creates only root-level config/catalog/profile files
   and the `goals/` container.
3. Update task setup and initialization so setup artifacts are deposited into
   `goals/<goal>/setup/`.
4. Update capability analysis naming from `agent-capabilities.*` to
   `agent-profile.*`, and document its relationship to `config.toml`.
5. Update report, logger, comments, promotion, retention, ledger recovery,
   merge repair, supervisor, git, GitHub, and evaluation adapters so no normal
   execution path writes root-level logs/reports/artifacts.
6. Keep backward-compatible reads for legacy paths during v1 cleanup, but new
   writes must use the cleaned layout.
7. Update docs and eval examples to reflect the cleaned layout.

## Acceptance Tests

- Unit tests prove the path helpers route logs, reports, artifacts, process
  state, setup artifacts, and profile/config files to the target layout.
- A fresh install test proves root-level `.long-horizon/` contains only the
  approved root files/directories and does not create `logs/`, `reports/`,
  `artifacts/`, `flows/`, `decisions/`, or `tasks/`.
- A task setup/init test proves setup files are under `goals/<goal>/setup/`.
- The calculator external eval proves:
  - `tmp/evals/long-horizon-calculator` is the target git repo;
  - no nested `target-repo` directory is created;
  - no outer eval `artifacts/` directory is created;
  - eval harness process logs are under the run process tree;
  - generated reports and chat artifacts remain under the run tree.
- Full test suite passes.

## Non-Goals

- Do not redesign the report UI in this cleanup.
- Do not remove `.agents/`; installed agent-facing rules and skills still live
  there.
- Do not implement a migration command for old live target repos unless tests
  show backward-compatible reads are not enough for v1.
