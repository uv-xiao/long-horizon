# Long-Horizon Configuration Catalog

This catalog lists configurable long-horizon policies for the target repository. Defaults should be reviewed during installation and may be overridden for a specific goal or active run when the task needs different behavior.

Each policy entry should record:

- current value;
- allowed values;
- storage location;
- validation rule;
- operational impact;
- helper skill or command for changing it.

## Agent Substrate

- `agent.substrate`: `codex-goal`, `codex`, `claude-code`, `humanize`, `native-process-agent`, or `manual`.
- `agent.goal_mode`: whether Codex `/goal` is used as the continuation mechanism.
- `agent.process_adapter`: how logical process operations map to the selected agent.
- `agent.operation_mode`: compatibility label only. The durable source of truth is `[features]`.
- `agent.capability_cache`: `.long-horizon/agent-capabilities.toml` stores a fingerprinted analysis of existing repo and target-agent features. Refresh it when agent instructions, hooks, skills, or target-agent selection change.
- `agent.native_feature_enablement`: native hooks, subagents, stop gates, review commands, or GUI/report features that should be enabled instead of reimplemented by the template.

## Feature Settings

- `features.runtime_state`: whether `.long-horizon/` owns durable goal/run/process/workflow state.
- `features.prompt_templates`: whether phase prompt templates are installed and used.
- `features.transition_validation`: always enabled when `runtime_state` is true.
- `features.message_mailboxes`: always enabled when `runtime_state` is true; creates per-process FIFO mailboxes.
- `features.local_supervisor`: optional future runtime supervisor; supervision is config, not a process kind.
- `features.native_agent_loop`: whether the selected target agent owns continuation/loop execution.
- `features.report_server`: whether local report serving is available.
- `features.github_channel`: whether GitHub issue/PR virtual channel operations are enabled.
- `profile.label`: derived from feature settings; not source of truth.
- `responsibility.*`: generated map of template-owned and target-agent-owned responsibilities.

## Process And Workspace

- `process.kind`: each process is either `workspace` or `virtual`. External services are virtual processes. `supervised` is not a process kind.
- `process.workspace_mode`: `original_checkout`, `worktree`, `branchless_read_only`, or `native_process`.
- `process.worktree_root`: where child worktrees are created.
- `process.branch_policy`: `code_changes_require_branch` or `read_only_branchless`.
- `process.branch_naming`: branch name template.
- `process.tmux_policy`: when tmux sessions are created or only recorded.
- `process.child_policy_update`: whether parent policy changes are pushed explicitly, adopted by regenerated brief, or handled by child respawn.
- `process.parent_wait_policy`: v1 uses flow-declared wait gates for child states, artifacts, checks, or quorum before parent advancement.
- `process.status_values`: `active`, `waiting`, `completed`, `cancelled`, `rejected`, `timed_out`, and `budget_exhausted`.

## Copy-On-Write State

- `state.model`: default `copy_on_write`.
- `state.snapshot_exclusions`: unsafe or impractical paths excluded from child snapshots.
- `state.snapshot_manifest_required`: whether child spawn must record copied and excluded paths.
- `state.merge_import_policy`: which child-produced deltas are imported into parent state.
- `state.process_flow`: each process owns `processes/<process-id>/flow.toml`.
- `state.flow_amendments`: workflow owner processes append amendments to `processes/<process-id>/flow-amendments.jsonl`.

## Process Mailboxes

- `mailbox.model`: per-process FIFO files.
- `mailbox.inbox`: `processes/<process-id>/mailbox/inbox.jsonl`.
- `mailbox.outbox`: `processes/<process-id>/mailbox/outbox.jsonl`.
- `mailbox.ack`: `processes/<process-id>/mailbox/ack.jsonl`.
- `mailbox.delivery`: async append-only delivery. Ack is optional and does not block delivery.
- `mailbox.report_projection`: mailbox messages are included in `report-data.json`, `progress.md`, and `progress.html`.

## Version Control

- `git.base_ref_policy`: how the review base is detected and pinned.
- `git.commit_policy`: when commits are recommended or automatic.
- `git.checkpoint_policy`: when checkpoint tags or branches are created.
- `git.pr_policy`: when work should become a PR.
- `git.merge_policy`: allowed merge, rebase, or cherry-pick strategies.

## Safety Boundaries

- `safety.secrets_auth`: approval policy for secrets and auth.
- `safety.destructive_git`: approval policy for reset, clean, force push, branch deletion, and history rewrite.
- `safety.network`: allowed network and remote execution behavior.
- `safety.command_allowlist`: optional command allowlist.
- `safety.sandbox`: `none`, `allowlist`, `container`, `remote`, or `approval_required`.
- `safety.dangerous_amendment_classes`: secrets/auth, destructive git, irreversible external effects, acceptance weakening, human-gate removal, and external issue/PR closing require human approval by default.

## Workflow Gates

- `workflow.transition_policy`: transition validation mode.
- `workflow.policy_change_transition_policy`: when active-run policy changes require a workflow transition.
- `workflow.human_gates`: states or risk classes requiring human approval.
- `workflow.retry_budget`: retry limits.
- `workflow.stop_conditions`: hard stop rules.
- `workflow.parallel_lanes`: disabled, allowed, or required.
- `workflow.join_gates`: flow-declared child process wait conditions before parent transition. v1 selectors are `all`, explicit process ids, and lane role selectors. Conditions are `completed`, `artifact_present`, `checks_passed`, `cancelled_or_rejected`, `timed_out`, `budget_exhausted`, or conjunctions of those conditions. Quorum counts only selected children satisfying the declared condition set. Terminal non-success states count only when explicitly listed.
- `workflow.wait_limits`: flow-declared timeout and budget limits for child processes.
- `workflow.wait_evaluation_artifacts`: where parent-side wait evaluation artifacts are written.

## Review And Evaluation

- `review.mode`: weak, strong, dynamic, or task-specific.
- `review.cadence`: when review runs.
- `critic.triggers`: conditions that call critic/watchdog review.
- `observer.board_policy`: separate observer boards for watchdog/meta-progress state.
- `observer.execution_modes`: checkpoint observer runs and long-running observer sidecars.
- `observer.workspace_policy`: attach to a task/parent process workspace by default; dedicated observer workspaces are optional for heavy tools, isolation, or multi-workspace monitoring.
- `observer.observe_grants`: target processes and read channels an observer may inspect.
- `observer.steer_grants`: target processes and input channels an observer may use to steer task execution.
- `observer.write_scope`: observer state writes are limited to observer boards, watchdog artifacts, and observer logs; task-process steering is governed separately by steer grants.
- `observer.capture_policy`: whether tmux pane capture or agent thread text can be read, and how unverified transcript claims are treated.
- `observer.intervention_policy`: append-only records required before or atomically with any observer steering message.
- `observer.health_fields`: drift score, retry pressure, evidence gaps, budget pressure, loop suspicion, and watchdog alerts.
- `evaluation.adapters`: benchmark, test, profiler, linter, or domain-specific evaluators.
- `evaluation.acceptance_evidence`: required evidence for completion.

## Artifacts, Logs, And Memory

- `artifacts.retention`: keep, compress, archive, externalize, or evict policy.
- `artifacts.large_file_policy`: limits for raw outputs and binary artifacts.
- `logging.level`: minimal, normal, verbose, or debug.
- `memory.deposition`: what becomes reusable memory.
- `adapters.learned_usage`: whether learned adapters may be used immediately.
- `adapters.promotion`: how learned adapters become reusable skills or memory.
- `deposition.promote_skill_template`: prompt/skill used to maintain `.agents/skills`.
- `deposition.promote_rule_template`: prompt/skill used to maintain `.agents/rules`.
- `deposition.promote_memory_template`: prompt/skill used to maintain memory files.
- `deposition.promote_adapter_template`: prompt/skill used to maintain adapter templates.

## Reporting

- `report.formats`: Markdown, HTML, JSON report data, CLI, GitHub, Feishu, or dashboard. Slide artifacts are not generated in v1 completion.
- `report.notification_channels`: where progress reports are sent.
- `report.workflow_visualization`: SVG/HTML workflow projection settings.
- `report.intervention_view`: compact intervention markers in the main timeline plus a detailed observer intervention lane/table.
- `report.agent_brief_filtering`: one brief schema with process-targeted observer findings and steering instructions, not separate audience-specific brief types by default.
- `report.timeline_analysis`: whether reporter-authored annotations, causal guesses, risk notes, and review questions may be written beside the source-backed timeline for human review.

## GitHub Virtual Channel

- `github.channel_process`: virtual process id for GitHub issue/PR operations.
- `github.operations`: create/comment/close issue, create/comment/close PR, import issue comments, and import PR comments.
- `github.auth`: repo-local `.gh/` or `tmp/gh/` only. Missing local auth must produce setup guidance instead of silently using global auth.
- `github.agent_skill_fallback`: operation envelopes may generate a strict brief telling the target agent to use installed GitHub skills when direct adapter execution is unavailable.

## Changing Policy

Use `configure-long-horizon` for installed defaults and `update-long-horizon-policy` for active-run overrides.

Every policy change should produce a decision artifact describing the requested change, reason, affected run or goal, validation performed, and rollback path.

Active-run policy changes are side artifacts by default. Require a workflow transition only when the change alters goal constraints, human gates, safety boundaries, acceptance evidence, or branch/process topology.

Policy changes do not automatically affect already-spawned child processes. Existing children keep their copied snapshot unless the parent explicitly pushes a scoped update, asks the child to adopt a regenerated brief, or respawns the child.
