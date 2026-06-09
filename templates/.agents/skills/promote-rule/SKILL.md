---
name: promote-rule
description: Promote a recurring repository rule into `.agents/rules/` with deposition evidence.
---

# Promote Rule

Use this when a run reveals a durable rule that future agents should follow.

## Workflow

1. Identify the repeated failure or successful constraint.
2. Decide whether it belongs in `.agents/rules/` instead of a skill.
3. Patch the smallest relevant rule file.
4. Record deposition evidence under `.long-horizon/artifacts/deposition/`.
5. Include rollback instructions and examples of when the rule does not apply.
