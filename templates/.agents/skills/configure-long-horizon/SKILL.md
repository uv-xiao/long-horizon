---
name: configure-long-horizon
description: Use when installing or updating long-horizon policy defaults for a target repository, especially when changing workspace, branch, snapshot, merge, commit, sandbox, review, reporting, evaluator, or adapter behavior.
---

# Configure Long-Horizon

Use this skill to inspect and modify installed long-horizon defaults. These defaults live outside any one active run and guide future goals unless a run overrides them.

## Workflow

1. Read `.long-horizon/config.toml`, `.long-horizon/config-catalog.md`, `.long-horizon/agent-capabilities.md`, and the repository's agent rules.
2. Identify the requested policy change and the affected catalog entries.
3. Compare the requested behavior with existing repository conventions, CI, PR rules, auth boundaries, and agent capabilities.
4. Propose a minimal config patch and explain operational consequences.
5. Run the repository's long-horizon validators if available.
6. Write a decision artifact under `.long-horizon/memory/policy-decisions/`.
7. Update `config.toml` and `config-catalog.md` only after the decision is clear.

## Required Checks

- Do not weaken secrets/auth, destructive-git, or irreversible-action gates without explicit human approval.
- Do not switch repository-editing child processes to branchless mode.
- Keep branchless mode limited to read-only research, inspection, reporting, and evaluation.
- Keep config changes auditable: every changed key needs a reason and rollback note.

## Output

Report:

- changed policy keys;
- why the change is needed;
- validation run;
- affected future goals;
- any active runs that need a separate `update-long-horizon-policy` decision.
