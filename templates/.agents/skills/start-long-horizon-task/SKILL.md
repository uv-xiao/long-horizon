---
name: start-long-horizon-task
description: Convert a human request into a task setup, selected operation mode, and scaffolds.
---

# Start Long-Horizon Task

Read `.agents/templates/long-horizon/task-setup.md`. Do not implement the task
during setup.

Use:

```bash
python -m long_horizon task setup --root . --request "<human request>"
```

Then inspect `.long-horizon/tasks/<task-id>/setup.md`,
`goal-contract.scaffold.md`, `flow-plan.md`, and `execution-brief.md`.
