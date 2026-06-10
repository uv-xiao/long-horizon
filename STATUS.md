# Status

This file is the repository's durable v1 feature ledger. It replaces the
narrower `TODO.md`: it records completed mechanisms, implementation evidence,
and verification evidence.

## Current Alignment

The current v1 direction is implemented as follows:

- feature settings are the source of truth;
- runtime-owned, native-agent, and hybrid are derived compatibility/profile
  labels, not hard source-of-truth modes;
- process kinds are only `workspace` and `virtual`;
- cross-process communication is through per-process FIFO mailboxes;
- task intake and goal/run initialization are separate phases;
- `progress.html`, `progress.md`, and `report-data.json` are the canonical
  report artifacts;
- report GUI evolution is handled through an explicit adapter boundary over
  `report-data.json`;
- every v1 mechanism has runtime behavior, installed prompt/skill guidance
  where user-facing, durable artifacts or ledgers, report projection, and
  system-test coverage.

Older negotiation documents have been removed from public docs after their
useful decisions were absorbed here, in README, and in the v1 completion goal.

## Implemented

| Feature | Evidence | Notes |
| --- | --- | --- |
| Safe installation into existing repos | `long_horizon/install.py`, installer and CLI system tests | Produces install plan, installs `.agents/`, runtime state, config, default flow, skills, templates, and gitignore entry. |
| Target-agent capability analysis | `long_horizon/capabilities.py`, `tests/test_st_v1_template_usability.py` | Writes structured and human-readable capability analysis, feature settings, responsibility map, and install decisions. |
| Feature settings as source of truth | `long_horizon/config.py`, `long_horizon/capabilities.py`, `tests/test_st_v1_completion_upgrade.py` | `[features]` drives runtime behavior. Compatibility labels/profile summaries are derived. |
| Prompt-first phase templates | `templates/prompts/*.md`, installable phase skills | Templates cover target analysis, install plan, task setup, goal contract, flow assembly, execution brief, observer intervention, join decision, completion, deposition, promotion, and merge repair. |
| Install/configuration skills | `templates/.agents/skills/analyze-target-agent`, `configure-long-horizon`, `install-long-horizon`, `plan-long-horizon-install`, `update-long-horizon-policy`; `tests/test_st_v1_status_completion.py` | Installed skills guide capability cache, feature settings, install plans, policy patches, approval evidence, and validation. |
| Task intake and initialization split | `long_horizon/task_setup.py`, v1 completion tests | Task intake records the request, capability fit, and suggested settings. Initialization creates the goal, run, root process, flow, mailboxes, and execution brief. |
| Goal/run creation | `long_horizon/goal.py`, runtime tests | Creates durable goals, run snapshots, boards, ledgers, primary process, reports, and process brief. |
| Structured workflow state | `long_horizon/workflow.py`, `long_horizon/transition.py` | TOML flows and Python validators enforce allowed transitions and gate evidence. |
| Artifact/check/human/wait gates | Transition tests and Humanize-style system tests | Transition validation checks recorded evidence. Tests/evals are workflow tasks whose evidence is then consumed by transitions. |
| Typed and loose logging | `long_horizon/logger.py`, unit tests | Canonical ledgers are typed, ordered, and hash-chained JSONL. Loose capture cannot drive transitions. |
| Two process kinds | `long_horizon/process.py`, unit/system tests | Only `workspace` and `virtual` are valid. External channels are virtual processes; supervision is config/runtime metadata. |
| Real process supervisor | `long_horizon/supervisor.py`, `python -m long_horizon supervisor ...`, `test_remaining_v1_features_are_runtime_backed_and_reported` | Starts real local OS subprocesses, records PID/session/log paths, supports status/reap/terminate, writes lifecycle events, and appears under `mechanism_evidence.supervisor`. |
| Process metadata and recovery | `long_horizon/process.py`, recovery tests | Processes have durable metadata, heartbeats, interruption, resume, and regenerated briefs. |
| Per-process FIFO mailboxes | `long_horizon/mailbox.py`, mailbox unit/system tests | Every process has `inbox.jsonl`, `outbox.jsonl`, and `ack.jsonl`; reports include mailbox messages and communication links. |
| Parent/child worktree model | `long_horizon/git_adapter.py`, git/worktree system tests | Spawns child worktrees, copies `.long-horizon/` state, imports selected child artifacts, and merges clean child branches. |
| Copy-on-write `.long-horizon/` state | Worktree system tests | Child state diverges locally until explicit parent-side import/merge. |
| Observer sidecars and interventions | `long_horizon/observer.py`, observer tests | Observers write append-only findings/interventions, can steer through granted channels, and do not mutate task boards. |
| Pushed human comment import | `long_horizon/comments.py`, report-server tests | Imports comment envelopes as typed human events with deduplication. Human and external channels are modeled as virtual-process style message sources. |
| Human notification channels | `long_horizon/notification.py`, `python -m long_horizon notify ...`, `test_remaining_v1_features_are_runtime_backed_and_reported` | Provides local and GitHub-backed virtual channel delivery, artifacts, mailbox routing, notification ledger events, and `mechanism_evidence.notifications`. |
| Full GitHub virtual channel envelope | `long_horizon/github_adapter.py`, `test_github_execution_failure_is_durable_channel_evidence`, GitHub channel tests | Supports issue/PR create/comment/close envelopes, inbound comments, mailbox routing, local-auth failure guidance, durable `github_operation_failed` events, operation artifacts, and skill-brief fallback. |
| Evaluation adapters | `long_horizon/evaluation.py`, `python -m long_horizon evaluation run ...`, `test_remaining_v1_features_are_runtime_backed_and_reported` | Implements reusable `command`, `file_contains`, and `metric_threshold` adapters with durable evaluation artifacts, events, and `mechanism_evidence.evaluations`. |
| Memory and knowledge deposition | `long_horizon/promotion.py`, promotion skills/templates, `test_installable_mechanism_skills_have_completion_contracts`, `test_remaining_v1_features_are_runtime_backed_and_reported` | Promotes reviewed artifacts into `.agents/skills`, `.agents/rules`, `.agents/adapters`, or `.long-horizon/memory` with evidence validation, rollback records, installed skill contracts, and report projection. |
| Artifact lifecycle sidecar | `long_horizon/retention.py`, `python -m long_horizon retention run ...`, `test_remaining_v1_features_are_runtime_backed_and_reported` | Compresses large artifacts by copy, writes a retention manifest, preserves source lineage, emits append-only retention events, and appears under `mechanism_evidence.retention`. |
| Ledger integrity recovery | `long_horizon/ledger_recovery.py`, `python -m long_horizon ledger reconcile ...`, `test_remaining_v1_features_are_runtime_backed_and_reported` | Detects sequence/hash-chain issues, preserves damaged ledgers, writes reconciled copies and reports, records recovery evidence, and appears under `mechanism_evidence.ledger_recovery`. |
| Git merge conflict repair | `long_horizon/merge_repair.py`, `python -m long_horizon merge-repair ...`, `test_source_backed_merge_repair_records_context_and_eval_evidence` | Records base/parent/child refs, merge failure event, conflict markers, eval refs, source notes, proposed patch before application, approval-gated apply/block evidence, and report projection. |
| Human-facing reports | `long_horizon/report.py`, report tests, `test_remaining_v1_features_are_runtime_backed_and_reported` | Generates `progress.html`, `progress.md`, and `report-data.json`; slide artifacts are not generated; `mechanism_evidence` indexes feature-specific events and artifacts. |
| Report GUI adapter boundary | `long_horizon/report_gui.py`, `python -m long_horizon report-gui ...`, `test_remaining_v1_features_are_runtime_backed_and_reported` | Writes `report-gui-manifest.json` so richer GUIs can render the same `report-data.json` model without changing runtime ledgers; visual polish is future adapter work. |
| Local report server | `long_horizon/report_server.py`, report-server tests | Serves canonical reports and accepts pushed comment envelopes through `POST /comments`. |
| Configuration catalog | `templates/.long-horizon/config-catalog.md` | Documents configurable policy knobs for runtime, process, notification, evaluation, retention, recovery, report GUI, and GitHub channels. |
| Prompt/deposition/repair skills | `templates/.agents/skills/*`, prompt/skill usability tests | Rating, improvement, install planning, promotion, deposition, operation, and merge-repair skills are installed and verified. |
| Pytest collection boundary | `pytest.ini` | Plain `pytest` limits collection to repository tests and ignores local research material under ignored directories. |
| Verification documentation | `docs/v1-feature-completion-audit.md`, `docs/v1-implementation-verification-guide.md`, `docs/v1-system-test-coverage.md`, `docs/v1-template-usability-verification.md` | Maps mechanisms to tests and artifacts for human review. |

## README Feature Coverage

| README Feature Area | Status |
| --- | --- |
| Install into existing repos and merge agent surfaces | Implemented with install plans, installed skills/templates, capability analysis, and feature settings. |
| Use as GitHub template/new repo base | Implemented by repository layout, installable template artifacts, and install/update workflow. |
| General, zero-overhead optional mechanisms | Implemented through feature settings, config catalog, prompt skills, and optional CLI/runtime modules. |
| Changelog for template evolution | Implemented in `CHANGELOG.md`. |
| Phase/mechanism/component architecture | Implemented in README/docs and reflected by skills/templates/runtime modules. |
| Installation and capability negotiation | Implemented. |
| Goal contract and judgment setup | Implemented as prompts/scaffolds plus runtime goal/run creation. |
| Flow assembly and workspace provisioning | Implemented for TOML flows, process-local flow, worktrees, and prompt templates. |
| Execution loop and review gates | Implemented with transitions, checks/evals, supervised subprocess support, reviews, and recovery. |
| Observer/watchdog/meta-progress | Implemented with observer processes, grants, interventions, and report projection. |
| Reporting, memory, and workflow evolution | Implemented with canonical reports, GUI adapter boundary, promotion/deposition, and flow amendments. |
| Runtime vs native-agent adaptation | Implemented as target capability analysis, feature settings, responsibility maps, and derived labels. |
| Logging and append-only ledgers | Implemented. |
| Human comments and intervention handling | Implemented for pushed comments, local/GitHub notification channels, observer steering, and mailbox routing. |
| Git/worktree/PR integration | Implemented for worktrees, copy-on-write state, clean merge, GitHub envelopes, local auth guidance, and conflict repair workflow. |
| Safety/configuration policy catalog | Implemented through config validation, catalog entries, dangerous-action approval gates, and policy skills. |
