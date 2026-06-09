---
name: promote-skill
description: Promote a learned repeatable behavior into a maintained `.agents/skills/<name>/SKILL.md`.
---

# Promote Skill

Use this as a deposition workflow task when a run produced a reusable behavior.

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

## Example

Promote a benchmark command sequence only after the run evidence shows it was
used successfully and the skill names the exact files it may edit.
