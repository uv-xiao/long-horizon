# Goal Contract Prompt

## Hard Constraints

- Goal contract creation is planning-only.
- Do not edit implementation files or start execution.
- Separate stable goal semantics from mutable plan details.

## Sequential Phases

1. Extract the objective, deliverables, and why the task matters.
2. Define hard constraints, non-goals, frozen files/APIs, safety boundaries,
   dependency policy, and budget.
3. Define open search space and allowed exploration methods.
4. Define acceptance criteria with falsifiable evidence artifacts.
5. Define verification commands, evaluator adapters, metrics, and failure
   thresholds.
6. Define human decision points and reviewer gates.
7. Run a challenge pass for vague deliverables, missing ACs, weak evidence, and
   unsafe assumptions.

## Review Gate

The contract cannot enter execution until acceptance criteria and evidence
artifacts are concrete enough for validators or human reviewers to judge.
