---
name: configure-long-horizon
description: Use when installing or updating long-horizon policy defaults for a target repository, especially when changing workspace, branch, snapshot, merge, commit, sandbox, review, reporting, evaluator, or adapter behavior.
---

# Configure Long-Horizon

## Purpose

Use this skill to inspect and modify installed long-horizon defaults. These defaults live outside any one active run and guide future goals unless a run overrides them.

## Scope

Configure feature settings, runtime/native-agent responsibility, workspace,
branch, snapshot, merge, commit, sandbox, review, reporting, evaluator,
notification, retention, recovery, and adapter behavior.

## Required Reads

- `.long-horizon/config.toml`
- `.long-horizon/config-catalog.md`
- `.long-horizon/agent-capabilities.md`
- repository agent rules
- active policy decision artifacts when present

## Allowed Writes

- `.long-horizon/config.toml`
- `.long-horizon/config-catalog.md` when policy docs change
- `.long-horizon/memory/policy-decisions/`
- proposed active-run policy artifacts

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

## Produced Artifacts

- config patch;
- policy decision artifact;
- validation output;
- rollback note.

## Commands

Use runtime validators and report generation when available. Use repository
tests when the config change affects execution behavior.

## Failure Handling

Stop and ask for human approval when the change weakens secrets/auth,
destructive-git, irreversible-action, human-gate, or acceptance criteria
policy. Record blocked decisions instead of silently mutating config.

## Completion Evidence

The config change is present, the decision artifact explains the reason and
rollback, validation passed or is explicitly blocked, and affected runs are
identified.

## Example

Enable GitHub notification channels only after the target repo has local
GitHub CLI auth configured and the decision artifact records the fallback path.
