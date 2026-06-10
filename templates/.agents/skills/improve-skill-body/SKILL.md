---
name: improve-skill-body
description: Improve an agent skill body so it gives clear task steps, artifacts, review gates, and examples.
---

# Improve Skill Body

Use this when a skill is too vague for a long-horizon process to follow
reliably.

## Workflow

1. Read the current skill and the task it is supposed to support.
2. Preserve the skill's intent and trigger scope.
3. Add or repair:
   - required reads;
   - allowed writes;
   - ordered steps;
   - produced artifacts;
   - failure handling;
   - validation or review gates;
   - one concrete example.
4. Keep the skill concise enough for an agent to load during task execution.
5. Record a review artifact under `.long-horizon/artifacts/skill-improvements/`.

## Example

When improving a deposition skill, include where the promoted skill is written,
where review evidence is stored, and what rollback file list is required.
