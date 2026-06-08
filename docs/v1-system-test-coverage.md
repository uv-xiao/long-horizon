# V1 System Test Coverage

This note records what the system-test suite proves for the v1 runtime and how
a human reviewer can inspect the generated artifacts.

## Test Commands

- `python -m unittest discover -s tests`
- Focused hard scenarios:
  - `python -m unittest tests.test_st_humanize_flows`
  - `python -m unittest tests.test_st_report_server_git_github`
  - `python -m unittest tests.test_st_cli_report_runtime`

## Feature Coverage

- **Install and target-repo layout**
  - Covered by `RuntimeSystemTests.create_installed_run`,
    `CliReportSystemTest`, and `ReportServerGitGithubSystemTests.make_git_run`.
  - Validates `.agents/`, `.long-horizon/`, `.gitignore`, config, default flow,
    goal/run state, and process metadata.

- **Goal/run lifecycle and workflow transitions**
  - Covered by `test_st_install_and_run_happy_path`,
    `test_humanize_v1_two_loops_with_inner_fork_join_and_real_human_observer_report`,
    and `test_humanize_v2_plan_lifecycle_rlcr_alignment_and_methodology_report`.
  - Validates artifact gates, check gates, human gates, wait gates, blocked
    transitions, applied transitions, terminal completion, and flow snapshot
    ownership.

- **Canonical and loose logging**
  - Covered by unit tests plus `test_st_install_and_run_happy_path`.
  - Validates typed JSONL ledgers, per-ledger sequence ids, hash chaining, and
    loose notes not advancing workflow state.

- **Humanize v1-style nested loop**
  - Covered by
    `test_humanize_v1_two_loops_with_inner_fork_join_and_real_human_observer_report`.
  - Validates two long-loop rounds, an inner fork-join exploration, candidate
    child processes, observer steering, child result import, wait-gate blocking
    until both candidates finish, human final acceptance, and completion.

- **Humanize v2-style workflow**
  - Covered by
    `test_humanize_v2_plan_lifecycle_rlcr_alignment_and_methodology_report`.
  - Validates plan expansion, adversarial critique, human plan acceptance,
    RLCR/delta-card evidence, full-alignment observer check, amendment approval,
    methodology deposition, and completion.

- **Process recovery**
  - Covered by `test_st_hard_recovery_case`.
  - Validates interrupted executor state, `agent-brief.md` regeneration,
    replacement session attachment, process event history, and continuation.

- **Observer and human involvement**
  - Covered by `test_st_parent_child_observer_comment_report`,
    the Humanize-style tests, and the report-server comment test.
  - Validates observer sidecar process metadata, observe/steer grants,
    append-only intervention events, no task-board mutation, pushed comment
    envelopes, immediate import as typed human events, classification, and
    report regeneration.

- **Report playback and slides**
  - Covered by every system test that calls `generate_report`, with stronger
    checks in `test_report_generate_writes_slides_and_server_imports_pushed_human_comment`.
  - Validates `report-data.json`, `progress.md`, `progress.html`,
    `slides-data.json`, and `slides.html`.
  - `report-data.json` must include event-sequence playback, snapshots, lanes,
    process/workflow nodes, communication edges, comments, observer
    interventions, and stable anchors.
  - `progress.html` must include the slider-backed event playback graph.
  - `slides.html` must include timeline slides, process map, human comments,
    observer interventions, and one slide per event.

- **Local report server**
  - Covered by
    `test_report_generate_writes_slides_and_server_imports_pushed_human_comment`.
  - Validates serving `progress.html`, `report-data.json`, `slides.html`,
    `slides-data.json`, and push-style `POST /comments` ingestion that imports
    human comments immediately and regenerates reports.

- **Real git worktree process model**
  - Covered by
    `test_real_git_worktree_spawn_copies_long_horizon_state_then_parent_imports_child_artifact`.
  - Uses a real temporary git repository with real `git worktree add`.
  - Validates child branch/worktree creation, copied `.long-horizon/` state,
    snapshot manifest, parent process metadata, child-local artifact creation,
    parent state remaining unchanged until explicit import, and parent-side
    import of selected child artifacts.

- **Parent-side child branch merge**
  - Covered by
    `test_parent_can_merge_child_branch_after_worktree_exploration`.
  - Uses a real child worktree branch, commits a tracked file in the child, then
    merges the child branch into the parent checkout.
  - Validates merged repository content and append-only
    `child_branch_merged` provenance in `process-events.jsonl`.

- **Cross-worktree `.long-horizon/` copy-on-write**
  - Covered by the same real worktree test.
  - Validates full logical `.long-horizon/` state copying into the child
    worktree and later divergence: child ledgers can record child-local
    artifacts without mutating the parent ledger until the parent imports
    selected results.

- **GitHub adapter**
  - Covered by `test_github_adapter_uses_repo_local_auth_and_normalizes_review_comments`.
  - Validates repo-local auth detection, no silent global auth fallback,
    normalized GitHub comment envelope writing, and a real `gh repo view` smoke
    when repo-local auth is available.

- **CLI usability**
  - Covered by `test_cli_driven_agent_mimic_generates_complete_playback_report`.
  - Validates the public `python -m long_horizon` path for install, goal/run
    creation, transitions, typed logging, and report generation.

## Human Review Guide

When a test fails or a reviewer wants to inspect an example run, reproduce a
focused scenario with one of the commands above, then inspect the temporary run
directory printed by a debugger or by adding a local breakpoint. The important
artifacts are:

- `.long-horizon/goals/<goal-id>/runs/<run-id>/boards/task.toml` for workflow
  state.
- `.long-horizon/goals/<goal-id>/runs/<run-id>/processes/*.toml` for process,
  branch, worktree, parent, observer, and session state.
- `.long-horizon/goals/<goal-id>/runs/<run-id>/logs/*.jsonl` for canonical
  append-only event evidence.
- `.long-horizon/goals/<goal-id>/runs/<run-id>/artifacts/snapshots/*.json` for
  worktree state-copy provenance.
- `.long-horizon/goals/<goal-id>/runs/<run-id>/artifacts/imports/` for
  parent-imported child results.
- `.long-horizon/goals/<goal-id>/runs/<run-id>/reports/progress.html` for the
  slider playback graph.
- `.long-horizon/goals/<goal-id>/runs/<run-id>/reports/slides.html` for the
  timeline slide view.
- `.long-horizon/goals/<goal-id>/runs/<run-id>/reports/report-data.json` and
  `slides-data.json` for deterministic machine-checkable report data.

For visual acceptance, open `progress.html` and move the event slider from the
first event to the last. The process map should reveal child processes,
observer/task edges, human comment markers, transition history, and artifact
imports over time. Open `slides.html` to inspect one event per slide with the
same timeline context.

## Remaining Deferred Features

- **Artifact retention/eviction/compression/externalization**: explicitly
  deferred until large real task artifacts need lifecycle policy.
- **Ledger repair tooling**: hash-chain append behavior is covered, but explicit
  repair and reconciliation commands are not implemented.
- **Remote execution, benchmark, GPU, and task-specific evaluator adapters**:
  intentionally outside the default v1 runtime.
- **Git merge conflict remediation**: clean child branch merge is covered, but
  conflict-resolution, rollback, and retry policy remain future mechanisms.
