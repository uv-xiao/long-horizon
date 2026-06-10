# Merge Conflict Repair Prompt

## Hard Constraints

- Inspect base, parent, child, and conflict markers before editing.
- Produce a proposed patch artifact before applying anything.
- Preserve parent intent and child evidence.
- Run selected eval tasks against the proposed patch.
- Require approval before dangerous merge application.

## Sequential Phases

1. Read the join/merge failure event and branch refs.
2. Classify the conflict type.
3. Inspect relevant files from base, parent, and child.
4. Write a proposed patch and rationale.
5. Run configured evals.
6. Request approval if the action is dangerous.
7. Apply or block and record merge-quality evidence.

## Source-Backed Checks

- Use Git's merge conflict workflow: inspect status/diffs, repair conflicted
  paths, stage resolved files, then continue.
- If rerere suggests a reused resolution, inspect the resulting diff before
  accepting it.
- If the conflict blocks a GitHub PR, resolve locally and push only after the
  proposed patch and eval evidence are accepted.

## Output Artifacts

- Proposed patch.
- Merge-quality evidence.
- Eval results.
- Approval evidence when required.
- Rollback instructions.
