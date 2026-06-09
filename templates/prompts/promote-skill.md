# Promote Skill Prompt

## Hard Constraints

- Promote only repeatable behavior with run evidence.
- Write maintained skill content, not an append-only dump.
- Keep secrets and private scratch paths out of the promoted skill.

## Sequential Phases

1. Read run artifacts, mailbox messages, eval evidence, and existing skills.
2. Decide whether this belongs as a skill instead of a rule, memory, or adapter.
3. Draft or patch `.agents/skills/<name>/SKILL.md`.
4. Write deposition evidence under `.long-horizon/artifacts/deposition/`.
5. Validate the skill has purpose, required reads, allowed writes, steps,
   failure handling, completion evidence, and examples.

## Output Artifacts

- Updated skill file.
- Deposition review artifact with problem, evidence, scope, counterexamples,
  validation, changed files, and rollback.
