# Task Setup Prompt

## Hard Constraints

- Do not implement the task during setup.
- Allowed writes are limited to `.long-horizon/tasks/<task-id>/` setup,
  contract scaffold, flow plan, and execution brief artifacts.

## Sequential Phases

1. Read the human request.
2. Reuse or refresh target-agent capability analysis.
3. Classify the task profile: planned implementation, open exploration,
   benchmark loop, research, debugging, review-only, or maintenance.
4. Confirm or override operation mode for this task.
5. Select phase templates and required evidence gates.
6. Declare expected process topology and human comment/notification policy.
7. Run `python -m long_horizon task setup --root . --request "<request>"`.

## Review Gate

Challenge whether the task requires fork/join, observer sidecars, benchmark
adapters, or stricter human gates before the goal contract starts.
