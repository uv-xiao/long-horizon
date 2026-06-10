# Execution Brief Prompt

## Hard Constraints

- Execution must follow the selected operation mode.
- Native-agent mode uses the target agent's loop; do not start a competing
  template loop.
- Runtime-owned mode uses template process/transition/report commands for
  canonical state.

## Sequential Phases

1. Read operation-mode decision, goal contract, flow plan, and current brief.
2. Verify preflight checks for the selected mode.
3. Attach the executor to the declared workspace and process state root.
4. Produce required artifacts for the current state.
5. Request transitions only after evidence exists.
6. Regenerate reports after major state changes.

## Runtime Commands

```bash
python -m long_horizon validate --root .
python -m long_horizon transition --root . --goal-id <goal> --run-id <run> --process-id <process> --to <state>
python -m long_horizon report generate --root . --goal-id <goal> --run-id <run>
```

## Review Gate

If the executor quits or the mode looks wrong, stop and regenerate a process
brief or rerun capability analysis before continuing.
