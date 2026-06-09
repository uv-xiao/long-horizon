---
name: merge-conflict-repair
description: Repair a merge conflict as a workflow task by proposing a patch first, then validating and applying only with required approval.
---

# Merge Conflict Repair

Use this when parent and child branches conflict during join or merge.

## Workflow

1. Inspect base, parent, child, and conflict markers.
2. Classify the conflict: textual overlap, semantic overlap, generated file,
   deleted/modified, dependency/config, or workflow-state conflict.
3. Preserve both parent intent and child evidence.
4. Write a proposed patch artifact before applying anything.
5. Run the selected eval tasks against the proposed patch.
6. If applying the patch is dangerous, require human approval evidence.
7. Apply or block, then record merge-quality evidence and rollback steps.

## Source-Backed Notes

- Git documents conflict repair as a three-way process: inspect the conflicted
  state, use `git diff` or a mergetool, mark resolved paths, then continue the
  merge.
- Git's rerere mechanism can reuse prior resolutions, but the workflow should
  still inspect the proposed result before accepting it.
- GitHub's command-line conflict workflow requires resolving local conflicts
  before pushing the result back to the remote PR.

## Example

For a `deleted by parent, modified by child` conflict, explain why the file
should remain deleted, be restored, or be split, then validate that acceptance
criteria still hold.
