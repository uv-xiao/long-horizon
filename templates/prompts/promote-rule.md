# Promote Rule Prompt

## Hard Constraints

- Promote only durable repo policy.
- Keep task-specific observations out of rules.
- Require approval for dangerous auth, git, external-state, or acceptance-gate
  changes.

## Sequential Phases

1. Read the triggering run evidence.
2. Locate the smallest `.agents/rules/` file to update.
3. Patch the rule with examples and non-applicability cases.
4. Write deposition evidence and rollback steps.

## Output Artifacts

- Updated `.agents/rules/*.md`.
- Deposition review artifact.
