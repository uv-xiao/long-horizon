---
name: promote-adapter
description: Promote a learned adapter or command bridge after a run proves it useful.
---

# Promote Adapter

## Purpose

Use this when a run learns how to operate a tool, benchmark, remote executor, or
service adapter.

## Scope

Promote adapter knowledge into `.agents/adapters/` or a skill only after the
adapter has usable evidence and clear failure modes.

## Required Reads

- adapter usage logs;
- command artifacts and failures;
- existing adapters and skills;
- auth/secrets policy.

## Allowed Writes

- `.agents/adapters/<adapter>.md` or a reviewed skill;
- deposition review artifacts;
- rollback notes.

## Workflow

1. Read adapter usage logs and artifacts.
2. Verify the adapter worked at least once and record known failure modes.
3. Write the adapter template or skill in the configured `.agents/` location.
4. Keep secrets/auth out of the adapter body.
5. Record deposition review evidence with validation and rollback.

## Produced Artifacts

- adapter template or skill;
- evidence of successful use;
- known failure modes;
- validation and rollback notes.

## Commands

Use runtime promotion commands when available. For command bridges, include the
exact command shape but not secrets or machine-local credentials.

## Failure Handling

Block promotion when the adapter only worked accidentally, requires hidden local
state, leaks auth material, or lacks a failure recovery path.

## Completion Evidence

The adapter body exists, evidence and failure modes are recorded, and reports
show the promotion event.

## Example

Promote a remote evaluation adapter only after a run logs the command, expected
inputs, output format, auth boundary, and retry behavior.
