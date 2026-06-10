---
name: promote-skill
description: Promote a learned repeatable behavior into a maintained `.agents/skills/<name>/SKILL.md`.
---

# Promote Skill

## Purpose

Use this as a deposition workflow task when a run produced a reusable behavior.

## Scope

Promote repeatable agent behavior into `.agents/skills/<name>/SKILL.md`.

## Required Reads

- run artifacts and logs that demonstrate the behavior;
- existing `.agents/skills/`;
- relevant repository rules;
- promotion prompt template when installed.

## Allowed Writes

- `.agents/skills/<skill-name>/SKILL.md`;
- deposition review artifacts under the active run;
- rollback notes.

## Workflow

1. Read the run evidence and usage logs.
2. Check the lesson is repeatable, scoped, and not already covered by an
   existing skill.
3. Write or update `.agents/skills/<skill-name>/SKILL.md`.
4. Write review evidence under `.long-horizon/artifacts/deposition/` with:
   - problem solved;
   - evidence from the run;
   - scope and limits;
   - counterexamples;
   - validation performed;
   - changed files;
   - rollback instructions.
5. Require human approval only for dangerous changes such as auth/secrets,
   destructive git, external-state closing, or acceptance weakening.

## Produced Artifacts

- promoted skill body;
- deposition review evidence;
- rollback instructions;
- validation notes.

## Commands

Use runtime promotion commands when available, or patch the skill file and record
the same review evidence manually.

## Failure Handling

Block promotion when evidence is one-off, overlaps an existing skill, weakens a
gate, includes secrets, or lacks validation.

## Completion Evidence

The promoted skill exists, review evidence names source artifacts and
validation, and reports include the promotion event.

## Example

Promote a benchmark command sequence only after the run evidence shows it was
used successfully and the skill names the exact files it may edit.
