---
name: promote-memory
description: Promote stable project knowledge into maintained memory files with review evidence.
---

# Promote Memory

## Purpose

Use this for reusable factual knowledge, not commands or policies.

## Scope

Promote stable lessons into maintained memory files when future tasks should
reuse the knowledge.

## Required Reads

- source artifacts and logs;
- existing memory files;
- repository rules governing stale knowledge;
- related skills or adapters.

## Allowed Writes

- configured memory files;
- deposition review artifacts;
- stale-condition and rollback notes.

## Workflow

1. Extract the stable lesson from artifacts and logs.
2. Verify it is not temporary task state.
3. Write the memory entry to the configured memory location.
4. Include source artifact refs, scope, stale conditions, and rollback path in
   `.long-horizon/artifacts/deposition/`.

## Produced Artifacts

- memory entry;
- source and scope evidence;
- stale-condition notes;
- rollback instructions.

## Commands

Use runtime promotion commands when available, or patch memory files and record
equivalent evidence manually.

## Failure Handling

Block promotion when the fact is uncertain, temporary, duplicated, or missing a
clear stale condition.

## Completion Evidence

The memory entry exists, source artifacts are cited, stale conditions are named,
and reports show the promotion event.

## Example

Promote a benchmark invocation path only if it is stable across runs and not
better expressed as an adapter skill.
