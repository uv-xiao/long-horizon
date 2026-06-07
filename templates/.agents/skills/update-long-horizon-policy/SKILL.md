---
name: update-long-horizon-policy
description: Use when changing long-horizon policy for an active goal or run, especially when task evidence shows the installed defaults are too strict, too loose, missing an adapter, or mismatched to the current execution process.
---

# Update Long-Horizon Policy

Use this skill for active-run policy changes. Installed defaults should remain stable unless the change is meant to affect future goals too.

## Workflow

1. Read the active goal contract, run config, process metadata, current boards, latest report, and `.long-horizon/config-catalog.md`.
2. Identify the policy override, scope, and reason.
3. Decide whether the change applies to one process, one lane, one run, one goal, or installed defaults.
4. If installed defaults should change, switch to `configure-long-horizon`.
5. Write a policy-change artifact under `runs/<run-id>/artifacts/policy-changes/`.
6. Apply the smallest config or run-state patch that expresses the override.
7. Decide whether the change requires a workflow transition.
8. Decide whether already-spawned children keep their snapshot, receive an explicit policy update, adopt a regenerated brief, or should be respawned.
9. Run validators and regenerate reports.

## Required Checks

- Do not change the goal contract silently; changed constraints require a goal-contract decision.
- Do not treat snapshot provenance as a merge gate unless concrete conflicts, changed constraints, failed checks, or human-risk gates require it.
- Do not import full failed child artifacts into parent state unless they are marked valuable evidence.
- Do not allow branchless mode for any process that may edit repository files.
- Treat active-run policy changes as side artifacts by default.
- Require a workflow transition only when the change alters goal constraints, human gates, safety boundaries, acceptance evidence, or branch/process topology.
- Do not mutate already-spawned child policy implicitly; record any explicit child update or respawn.
- Secrets/auth, destructive git, and irreversible/high-risk actions still require explicit human approval.

## Policy-Change Artifact

Record:

- requested change;
- scope;
- old value and new value;
- reason and evidence;
- expected effect on current process/run;
- validation performed;
- whether a workflow transition was required and why;
- child process propagation decision;
- rollback path;
- whether the installed default should later be updated.
