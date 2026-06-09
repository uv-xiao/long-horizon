---
name: plan-long-horizon-install
description: Plan a long-horizon template installation or update before mutating target repo agent files.
---

# Plan Long-Horizon Install

Use this before installing or updating `.agents/` and `.long-horizon/`.

## Workflow

1. Inspect existing agent surfaces: `AGENTS.md`, `.agents/`, native hooks,
   GitHub rules, CI, and workflow docs.
2. Inspect `.long-horizon/agent-capabilities.toml` when present.
3. Choose feature settings, not broad modes, as the source of truth.
4. Write `.long-horizon/install-plan.md` with:
   - files to create or update;
   - feature settings;
   - responsibility map;
   - ambiguous merges needing human review;
   - validation commands;
   - rollback path.
5. Apply only after the plan is accepted or the merge is unambiguous.

## Example

For Codex `/goal`, enable `runtime_state`, `transition_validation`,
`message_mailboxes`, `prompt_templates`, `native_agent_loop`, and
`report_server`.
