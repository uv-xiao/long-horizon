# Install Plan Prompt

## Hard Constraints

- Produce an install plan before changing agent-facing files.
- Do not overwrite existing agent instructions without classifying merge,
  extend, replace, or leave-alone.
- Allowed writes before approval: `.long-horizon/install-plan.md` and decision
  artifacts.

## Sequential Phases

1. Read capability analysis and selected operation mode.
2. List existing agent/rule/hook/workflow surfaces.
3. List skills, prompts, hooks, runtime files, and config changes to install.
4. Mark native-agent features to enable instead of duplicating.
5. Mark disabled mechanisms and why.
6. Ask for human approval if a merge is ambiguous.
7. Apply install with `python -m long_horizon install --target . --apply` only
   after approval or when the plan is unambiguous.

## Review Gate

Check that runtime-owned mode installs full runtime artifacts and native-agent
mode does not install a competing loop.
