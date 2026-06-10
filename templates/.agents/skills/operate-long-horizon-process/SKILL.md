---
name: operate-long-horizon-process
description: Handle checkpoints, observer interventions, fork/join, recovery, and active-run policy changes.
---

# Operate Long-Horizon Process

## Purpose

Operate an active long-horizon process without bypassing the runtime state
model.

## Scope

Use for checkpoints, observer interventions, fork/join, recovery, active-run
policy changes, supervisor handoff, notification routing, and completion
preparation.

## Required Reads

- `.long-horizon/config.toml`
- the process `flow.toml`
- the process mailbox files
- recent run ledgers and reports
- the relevant prompt templates:

- `.agents/templates/long-horizon/observer-intervention.md`
- `.agents/templates/long-horizon/join-decision.md`
- `.agents/templates/long-horizon/execution-brief.md`

## Allowed Writes

- process-owned artifacts under the active run;
- process outbox messages;
- observer/intervention artifacts when granted;
- proposed flow amendments;
- generated briefs and reports through runtime commands.

Do not mutate workflow boards directly.

## Workflow

1. Read current process metadata, `flow.toml`, mailbox state, and report data.
2. Classify the operation: checkpoint, steer, fork, join, recover, notify, or
   complete.
3. Use mailbox messages or prompt templates to steer other processes.
4. Write artifacts before asking for a transition.
5. Ask the transition command to advance only after declared evidence exists.

## Produced Artifacts

- mailbox messages;
- process artifacts;
- observer intervention records;
- join/import evidence;
- regenerated `agent-brief.md` and reports.

## Commands

Use `python -m long_horizon process ...`, `mailbox ...`, `transition ...`, and
`report generate ...` commands when available.

## Failure Handling

If evidence is missing, write a blocker artifact and notify the parent or
observer process. If a process exits or loses its agent session, regenerate the
brief and resume against the existing process state.

## Completion Evidence

Completion evidence is a transition event, required artifacts, acked critical
messages when configured, and report data showing the process state.

## Example

For a fork/join loop, child processes write candidate artifacts and mailbox the
parent. The parent imports selected artifacts, records rejection summaries for
other children, then requests the join transition.
