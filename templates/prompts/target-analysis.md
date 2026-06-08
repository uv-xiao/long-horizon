# Target Analysis Prompt

## Hard Constraints

- Do not modify repository source code during analysis.
- Allowed writes are limited to `.long-horizon/agent-capabilities.toml`,
  `.long-horizon/agent-capabilities.md`, `.long-horizon/install-plan.md`, and
  `.long-horizon/decisions/operation-mode.md`.
- Reuse cached capability analysis when the fingerprint is fresh.

## Sequential Phases

1. Inspect repo instructions: `AGENTS.md`, `CLAUDE.md`, `.agents/`, `.claude/`,
   `.cursor/`, workflow docs, CI, scripts, hooks, and issue/PR conventions.
2. Inspect target-agent features: persistence, hooks, stop gates, subagents,
   review commands, process/session management, GUI/report support, and auth
   prerequisites.
3. Classify capabilities as native-agent, template-runtime, or unavailable.
4. Choose `runtime-owned`, `native-agent`, or `hybrid` mode.
5. Write the capability cache and operation-mode decision.
6. Run `python -m long_horizon capabilities analyze --root .` or the
   equivalent runtime command when the Python runtime is used.

## Review Gate

Before install, challenge whether the selected mode duplicates a native loop or
under-provisions a weak agent.
