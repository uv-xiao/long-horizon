# Completion Audit Prompt

## Hard Constraints

- Completion is unproven until every acceptance criterion has direct evidence.
- Do not mark complete based on intent, partial progress, or broad tests that do
  not cover the requirement.

## Sequential Phases

1. Enumerate every requirement, artifact, gate, command, invariant, and
   deliverable from the goal contract and flow.
2. Identify evidence that would prove each item.
3. Inspect current files, ledgers, reports, tests, PR state, and runtime
   behavior.
4. Mark each item proven, contradicted, incomplete, weak, or missing.
5. Resolve gaps or record explicit deferrals with impact.
6. Run final validators/tests.
7. Transition to complete only when evidence proves completion.

## Review Gate

If any evidence is weak or indirect, keep the workflow active.
