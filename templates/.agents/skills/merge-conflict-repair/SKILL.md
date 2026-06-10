---
name: merge-conflict-repair
description: Repair a merge conflict as a workflow task by proposing a patch first, then validating and applying only with required approval.
---

# Merge Conflict Repair

## Purpose

Use this when parent and child branches conflict during join or merge.

## Scope

Repair merge conflicts as a workflow task by preserving source context,
proposing a patch first, validating it, and applying only when the required
approval and eval evidence exists.

## Required Reads

- merge failure event;
- base, parent, and child refs;
- conflicted file content and git status;
- process join/import policy;
- selected eval tasks and approval policy.

## Allowed Writes

- merge-repair artifacts under the active run;
- proposed patch files;
- eval artifacts;
- final repaired files only after approval when required.

## Workflow

1. Inspect base, parent, child, and conflict markers.
2. Classify the conflict: textual overlap, semantic overlap, generated file,
   deleted/modified, dependency/config, or workflow-state conflict.
3. Preserve both parent intent and child evidence.
4. Write a proposed patch artifact before applying anything.
5. Run the selected eval tasks against the proposed patch.
6. If applying the patch is dangerous, require human approval evidence.
7. Apply or block, then record merge-quality evidence and rollback steps.

## Produced Artifacts

- conflict source summary;
- proposed patch;
- eval results;
- apply/block record;
- rollback notes.

## Commands

Use `git status`, `git diff`, `git show`, runtime evaluation commands, and the
runtime merge-repair command when available.

## Failure Handling

Block application if source context is missing, evals fail, conflict ownership
is unclear, approval is required but absent, or the repair weakens acceptance
criteria.

## Completion Evidence

Reports show the merge failure, source refs, proposed patch, eval evidence,
approval when required, and final apply/block event.

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
