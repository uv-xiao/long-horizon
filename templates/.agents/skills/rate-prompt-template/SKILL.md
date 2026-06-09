---
name: rate-prompt-template
description: Rate a long-horizon prompt template for task readiness before it is used or promoted.
---

# Rate Prompt Template

Use this on a prompt template before a long-horizon task depends on it.

## Workflow

1. Read the prompt and the task/goal context it is meant to guide.
2. Score each item as `pass`, `partial`, or `missing`:
   - purpose and scope;
   - required reads;
   - allowed writes;
   - sequential steps;
   - produced artifacts;
   - commands/tools used;
   - review or failure handling;
   - completion evidence;
   - concrete examples;
   - no hidden implementation work inside a planning-only prompt.
3. Write a short rating artifact under `.long-horizon/artifacts/prompt-ratings/`.
4. If any required item is missing, propose a patch before the prompt is used.

## Example Output

```markdown
# Prompt Rating

- prompt: `templates/prompts/goal-contract.md`
- verdict: `partial`
- missing: completion evidence, failure handling
- action: patch before use
```
