# V1 Feature Completion Audit

This audit maps the completion goal to current evidence. It is intentionally
evidence-first: a feature is implemented only when runtime behavior,
agent-facing guidance, durable artifacts, report projection, and system tests
line up.

## Requirement Matrix

| Requirement | Runtime Evidence | Prompt/Skill Evidence | Report Evidence | Test Evidence | Status |
| --- | --- | --- | --- | --- | --- |
| Feature settings are source of truth | `long_horizon/config.py`, `long_horizon/capabilities.py` | `configure-long-horizon`, install/config prompts | `feature_settings`, `profile`, `responsibility_map` in `report-data.json` | `test_feature_settings_install_and_task_initialization` | Implemented |
| Only `workspace` and `virtual` process kinds | `long_horizon/process.py` rejects other kinds | process-operation skills describe runtime/native-agent responsibility | process nodes in `report-data.json` | `test_two_process_kinds_and_mailbox_fifo` | Implemented |
| Per-process FIFO mailboxes | `long_horizon/mailbox.py` writes inbox/outbox/ack JSONL | operation and notification skills route through mailboxes | `mailboxes`, `mailbox_messages`, `communication_edges` | `test_two_process_kinds_and_mailbox_fifo` | Implemented |
| Per-process `flow.toml` and copy-on-write state | `long_horizon/process.py`, `long_horizon/git_adapter.py` | fork/join and operation skills require parent-side import | process flow state and spawn/import events | `test_real_worktree_copy_on_write_flow_and_import` | Implemented |
| Task intake separate from initialization | `long_horizon/task_setup.py` | task setup and goal contract prompts | initialization reports and briefs | `test_feature_settings_install_and_task_initialization` | Implemented |
| Local supervisor as runtime metadata | `long_horizon/supervisor.py` | `operate-long-horizon-process` covers supervisor handoff and recovery | `mechanism_evidence.supervisor`, process events, artifacts | `test_remaining_v1_features_are_runtime_backed_and_reported` | Implemented |
| Notification channels as virtual-process communication | `long_horizon/notification.py`, `long_horizon/github_adapter.py` | notification and operation guidance in installed skills | `mechanism_evidence.notifications`, mailbox links | `test_remaining_v1_features_are_runtime_backed_and_reported` | Implemented |
| GitHub issue/PR virtual channel and auth failure evidence | `long_horizon/github_adapter.py` writes operation artifacts and failure events | GitHub brief fallback plus repo-local auth rule | `mechanism_evidence.github_operations`, `github_operation_failed` | `test_github_execution_failure_is_durable_channel_evidence`, `test_dangerous_approval_full_github_channel_and_auth_failure_guidance` | Implemented |
| Evaluation adapters as workflow-task evidence | `long_horizon/evaluation.py` | config and operation skills describe eval selection | `mechanism_evidence.evaluations`, evaluation artifacts | `test_remaining_v1_features_are_runtime_backed_and_reported` | Implemented |
| Promotion/deposition through review artifacts | `long_horizon/promotion.py` | promote skill/rule/memory/adapter skills include completion contracts | `mechanism_evidence.promotion`, deposition artifacts | `test_installable_mechanism_skills_have_completion_contracts`, `test_remaining_v1_features_are_runtime_backed_and_reported` | Implemented |
| Retention sidecar preserves lineage | `long_horizon/retention.py` | deposition/config guidance routes retention as sidecar policy | `mechanism_evidence.retention`, retention manifest | `test_remaining_v1_features_are_runtime_backed_and_reported` | Implemented |
| Ledger recovery preserves damaged input and reconciled output | `long_horizon/ledger_recovery.py` | operation skill covers recovery handoff | `mechanism_evidence.ledger_recovery`, reconciliation artifacts | `test_remaining_v1_features_are_runtime_backed_and_reported` | Implemented |
| Source-backed merge-conflict repair | `long_horizon/merge_repair.py` records base/parent/child refs, failure event, markers, eval refs, source notes, proposed patch, and approval | `merge-conflict-repair` skill defines source-backed workflow | `mechanism_evidence.merge_repair`, proposed patch and repair record | `test_source_backed_merge_repair_records_context_and_eval_evidence` | Implemented |
| Canonical human reports and no slide artifacts | `long_horizon/report.py`, `long_horizon/report_server.py` | report guidance keeps views human-oriented | `progress.html`, `progress.md`, `report-data.json`, `mechanism_evidence` | report server tests and status completion tests | Implemented |
| GUI adapter boundary | `long_horizon/report_gui.py` | config catalog documents adapter boundary | `report-gui-manifest.json`, `mechanism_evidence.report_gui` | `test_remaining_v1_features_are_runtime_backed_and_reported` | Implemented |
| Installed skill completion contracts | template skills under `templates/.agents/skills/` | installed skills include purpose, scope, reads, writes, workflow, artifacts, commands, failure handling, completion evidence, examples | install report data confirms installed feature settings | `test_installable_mechanism_skills_have_completion_contracts` | Implemented |

## Audit Notes

- Python modules are treated as runtime substrate. The implemented claim depends
  on their integration into ledgers, artifacts, reports, and installed skills.
- `report-data.json` now contains `mechanism_evidence`, a typed index that lets
  humans and tests inspect mechanism-specific events and artifacts without
  scraping generic event rows.
- GitHub direct execution failures are durable channel evidence. Missing
  repo-local auth produces setup guidance and a `github_operation_failed` event
  instead of silently using unrelated credentials.
- Merge repair records source context and proposed patches before application.
  Application remains approval-gated when requested.
- Richer GUI surfaces remain future adapter work over `report-data.json`; the
  current v1 completion bar is data completeness, not visual polish.
