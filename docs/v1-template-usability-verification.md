# V1 Template Usability Verification

This note maps the v1 prompt-first usability goal to implementation artifacts
and tests.

## What This V1 Completion Adds

The v1 completion makes the template prompt-first while keeping the Python
runtime available as one substrate.

- Target-agent capability analysis is implemented in `long_horizon/capabilities.py`.
- Operation modes are `runtime-owned`, `native-agent`, and `hybrid`.
- Capability decisions are cached in `.long-horizon/agent-capabilities.toml`
  and explained in `.long-horizon/agent-capabilities.md` plus
  `.long-horizon/decisions/operation-mode.md`.
- Task setup is implemented in `long_horizon/task_setup.py` and writes
  `.long-horizon/tasks/<task-id>/` setup, contract, flow, and execution
  artifacts.
- Installable phase skills live under `templates/.agents/skills/`.
- Prompt templates live under `templates/prompts/` and are installed into
  `.agents/templates/long-horizon/`.
- Reports and agent briefs include operation-mode provenance and
  responsibility splits.

## Test Commands

```bash
python -m unittest tests.test_st_v1_template_usability
python -m unittest discover -s tests
```

## Coverage

- **Weak target agent**:
  `test_weak_agent_installs_runtime_owned_mode_and_phase_templates` installs
  into a repo without native orchestration and validates runtime-owned mode,
  runtime directories, installed phase skills, installed prompts, and task setup
  artifacts.

- **Strong native target agent**:
  `test_strong_native_agent_uses_native_agent_mode_without_competing_loop`
  installs into a repo with native hooks/subagents/review/process features and
  validates native-agent mode plus install-plan text that avoids a competing
  loop.

- **Capability cache**:
  `test_capability_cache_reuses_and_invalidates_on_agent_surface_change`
  proves cached analysis is reused when inputs are unchanged and refreshed when
  agent-facing inputs change.

- **Report and brief provenance**:
  `test_report_and_agent_brief_include_operation_mode_provenance` proves
  `report-data.json`, `progress.md`, and `agent-brief.md` expose the selected
  operation mode and capability-analysis evidence.

## Human Review

After installing into a target repo, inspect:

- `.long-horizon/agent-capabilities.toml`
- `.long-horizon/agent-capabilities.md`
- `.long-horizon/decisions/operation-mode.md`
- `.long-horizon/install-plan.md`
- `.agents/skills/*/SKILL.md`
- `.agents/templates/long-horizon/*.md`
- `.long-horizon/tasks/<task-id>/setup.md`
- `.long-horizon/tasks/<task-id>/goal-contract.scaffold.md`
- `.long-horizon/tasks/<task-id>/flow-plan.md`
- `.long-horizon/tasks/<task-id>/execution-brief.md`

The prompt templates should be usable without knowing this repository's Python
internals: each one declares hard constraints, sequential phases, expected
writes, and review or validator gates.
