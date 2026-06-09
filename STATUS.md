# Status

This file is the repository's feature ledger. It replaces the narrower
`TODO.md`: it records what is implemented, what is partial, what remains planned,
and which older TODO items were reframed or made obsolete by later design work.

## Status Labels

- **Implemented**: present in code/templates/docs and covered by tests or
  verification notes.
- **Partial**: a working slice exists, but README-level ambition is broader.
- **Planned**: intentionally not implemented yet.
- **Outdated**: an older TODO is no longer the right framing.

## Implemented

| Feature | Evidence | Notes |
| --- | --- | --- |
| Safe installation into existing repos | `long_horizon/install.py`, `python -m long_horizon install`, installer system tests | Produces `.long-horizon/install-plan.md`, installs `.agents/`, runtime state, config, default flow, and gitignore entry. |
| Target-agent capability analysis | `long_horizon/capabilities.py`, `tests/test_st_v1_template_usability.py` | Writes `.long-horizon/agent-capabilities.toml`, `.long-horizon/agent-capabilities.md`, and `.long-horizon/decisions/operation-mode.md`. |
| Capability cache reuse and invalidation | `long_horizon/capabilities.py`, `test_capability_cache_reuses_and_invalidates_on_agent_surface_change` | Fingerprints relevant agent/repo inputs and refreshes when those inputs change. |
| Operation modes | `agent.operation_mode` config, capability decision docs, v1 usability tests | Supports `runtime-owned`, `native-agent`, and `hybrid` as v1 operating modes. This is not a separate product line. |
| Prompt-first phase templates | `templates/prompts/*.md` | Templates cover target analysis, install plan, task setup, goal contract, flow assembly, execution brief, observer intervention, join decision, completion audit, and deposition review. |
| Installable phase skills | `templates/.agents/skills/*/SKILL.md` | Skills guide analyze/install/task/contract/flow/execution/operation/completion phases. |
| Task setup artifacts | `long_horizon/task_setup.py`, v1 usability tests | Writes `.long-horizon/tasks/<task-id>/setup.md`, contract scaffold, flow plan, and execution brief. |
| Goal/run creation | `long_horizon/goal.py`, runtime tests | Creates durable goals, run snapshots, boards, ledgers, primary process, reports, and brief. |
| Structured workflow state | `long_horizon/workflow.py`, `long_horizon/transition.py` | TOML flow snapshots and boards, Python transition validators, allowed transitions. |
| Artifact/check/human/wait gates | Transition tests and Humanize-style system tests | Gates block or apply transitions based on source-backed evidence. |
| Typed and loose logging | `long_horizon/logger.py`, unit tests | Canonical typed ledgers are hash-chained JSONL; loose capture cannot drive transitions. |
| Process metadata and recovery | `long_horizon/process.py`, recovery tests | Processes have durable TOML metadata, heartbeats, interruption, resume, and regenerated briefs. |
| Parent/child worktree model | `long_horizon/git_adapter.py`, git/worktree system tests | Spawns child worktrees, copies `.long-horizon/` state, imports selected child artifacts, and merges clean child branches. |
| Copy-on-write `.long-horizon/` state | Git/worktree system tests | Child state diverges locally until parent-side import/merge. |
| Observer sidecars and intervention records | `long_horizon/observer.py`, observer tests | Observers write append-only findings/interventions and do not mutate task boards. |
| Pushed human comment import | `long_horizon/comments.py`, report server tests | Imports comment envelopes as typed human events with deduplication. |
| Human-facing reports | `long_horizon/report.py`, report tests | Generates `progress.html`, `progress.md`, `report-data.json`, and compatibility slide aliases. |
| Local report server | `long_horizon/report_server.py`, report-server tests | Serves reports and accepts pushed comment envelopes through `POST /comments`. |
| Operation-mode provenance in reports/briefs | `long_horizon/report.py`, v1 usability tests | Report data, Markdown, HTML, and `agent-brief.md` expose the selected mode and responsibility split. |
| GitHub adapter local-auth rule | `long_horizon/github_adapter.py`, GitHub adapter tests | Uses repo-local `.gh/` or `tmp/gh/` auth and emits setup guidance when unavailable. |
| Configuration catalog | `templates/.long-horizon/config-catalog.md` | Documents configurable policy knobs, including operation mode and capability cache. |
| Verification documentation | `docs/v1-implementation-verification-guide.md`, `docs/v1-system-test-coverage.md`, `docs/v1-template-usability-verification.md` | Maps mechanisms to artifacts and tests for human review. |

## Partial

| Feature | Current State | Remaining Work |
| --- | --- | --- |
| Process model as real running processes | V1 has durable logical process metadata, worktrees, tmux/session fields, interruption/resume, and sidecar concepts. | Implement a real supervisor that runs task, observer, reporter, retention, recovery, and repair processes as supervised OS processes or adapter-backed handles. |
| Native-agent integration | V1 chooses native-agent/hybrid modes and installs prompts without duplicating native loops. | Add richer agent-specific probes and feature enablement for concrete agents beyond generic filesystem heuristics. |
| Memory and knowledge deposition | V1 has deposition prompts and memory directories; learned adapters can be logged as artifacts. | Implement reviewer workflows that promote stable lessons/adapters into reusable skills or memory after evidence review. |
| Evaluation adapters | V1 supports check events and task-specific artifacts; tests mimic benchmark/review flows. | Add reusable benchmark/profiler/evaluator adapter packs when real task domains need them. |
| Human notification channels | V1 supports local reports, pushed comments, and local report server. | Add configured external notification channels such as GitHub issue comments, Feishu, or richer dashboards. |
| Git merge handling | V1 supports clean child branch merge with provenance. | Add conflict-resolution workflow, rollback/retry policy, and merge-quality evals. |
| Report UI | V1 has a static HTML/SVG/Markdown human report and deterministic `report-data.json`. | Replace or augment with richer GUI adapters while preserving the report data boundary. |
| Artifact lifecycle | V1 preserves append-only artifacts and import provenance. | Add sidecar retention/compression/externalization while preserving lineage and audit trust. |
| Ledger integrity recovery | V1 writes hash-chained append-only ledgers. | Add privileged repair/reconciliation process that preserves damaged inputs and emits a reconciliation report. |

## Planned

- Implement a real process supervisor. V1 records logical processes in files;
  the next essential layer should run task, observer, reporter, retention,
  recovery, and other meta-processes as supervised OS processes or
  adapter-backed handles with durable PID/session metadata, heartbeats, restart
  policy, and append-only lifecycle events. Async Python may be used inside a
  worker when useful, but it is not the process model.
- Model post-run adapter and skill promotion as a process-ending review step.
  Runs can learn and use missing adapters while logging them under run
  artifacts; promotion should inspect adapter usage logs, run review/eval
  checks, and propose reusable skills or memory updates.
- Model artifact retention and eviction as a sidecar process. Evidence
  artifacts remain append-only by default, while a retention sidecar detects
  large or stale artifacts, compresses/externalizes them under policy, and
  preserves lineage plus completion-audit trust.
- Replace or augment the v1 report UI with a richer GUI surface. Future work
  should evaluate GUI substrates such as OMP/oh-my-pi, Warp-style interactive
  views, or a custom frontend for process/workflow timelines, comments,
  intervention handling, and artifact inspection.
- Define a report GUI adapter boundary beyond the current static report. The
  durable report data should remain independent from any specific GUI so future
  frontends can render the same process/workflow/event model without changing
  runtime ledgers.
- Model git merge conflict remediation as a workflow step. Future conflict
  handling should spawn a repair process with evals that judge whether the merge
  preserves parent intent, child evidence, tests, and workflow state.
- Implement ledger repair and reconciliation as a privileged recovery process.
  Corrupted or partially copied ledgers should be repaired only by a dedicated
  process that records provenance, preserves damaged inputs, and emits a
  reconciliation report.

## Outdated Or Reframed TODOs

- **"Define post-run adapter promotion" as a hard-coded mechanism** is
  outdated. It is now treated as a configurable process-ending review/deposition
  workflow.
- **"Add artifact retention and eviction mechanism" as a core runtime feature**
  is reframed as a sidecar process so normal runs pay no overhead until large
  artifacts require lifecycle policy.
- **"Add git merge conflict remediation policy" as a static policy document** is
  reframed as a workflow step with explicit evals and repair-process evidence.
- **"Add explicit ledger repair/reconciliation tooling" as a normal user tool**
  is reframed as a privileged recovery process because ledger repair changes
  audit evidence.
- **Separate-version usability layer naming** is obsolete. Prompt-first
  usability, operation-mode selection, and capability analysis are part of
  completing v1.

## README Feature Coverage

| README Feature Area | Status |
| --- | --- |
| Install into existing repos and merge agent surfaces | Implemented with mode-aware install plan; ambiguous human-review flow is prompt-guided and partially automated. |
| Use as GitHub template/new repo base | Partial: repo layout and templates support it, but no dedicated GitHub template packaging workflow exists. |
| General, zero-overhead optional mechanisms | Partial: mechanisms are configurable and prompt-guided; more dynamic enable/disable policy can be added. |
| Changelog for template evolution | Implemented in `CHANGELOG.md`. |
| Phase/mechanism/component architecture | Implemented in README/docs and reflected by skills/templates/runtime modules. |
| Installation and capability negotiation | Implemented. |
| Goal contract and judgment setup | Implemented as prompts/scaffolds; runtime goal creation is implemented. |
| Flow assembly and workspace provisioning | Implemented for TOML flows, worktrees, and prompt templates; H2-style cartridges remain future/optional. |
| Execution loop and review gates | Partial: runtime transitions/reviews exist; full real process supervisor remains planned. |
| Observer/watchdog/meta-progress | Partial: observer sidecars and interventions are modeled/logged; real long-running supervised observers remain planned. |
| Reporting, memory, and workflow evolution | Partial: reports and deposition prompts exist; richer GUI and memory promotion workflows remain planned. |
| Runtime vs native-agent adaptation | Implemented as v1 operation modes with capability analysis and install/task artifacts. |
| Logging and append-only ledgers | Implemented. |
| Human comments and intervention handling | Implemented for local push inbox/server; external notification channels remain planned. |
| Git/worktree/PR integration | Partial: local git/worktree and GitHub adapter auth are implemented; richer PR workflows and conflict repair remain planned. |
| Safety/configuration policy catalog | Implemented as a catalog and validators for core config; deeper safety enforcement remains task/config-specific. |
