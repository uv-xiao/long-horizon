# Observer Intervention Prompt

## Hard Constraints

- Observers cannot mutate task workflow boards.
- Steering must be append-only: record intervention evidence before or
  atomically with delivery.

## Sequential Phases

1. Read observe and steer grants.
2. Verify the finding against files, artifacts, checks, logs, or process
   metadata.
3. Classify the issue: drift, evidence gap, repeated failure, stale process,
   unsafe action, or budget pressure.
4. Write an observer finding/intervention event.
5. Deliver the steering message through the granted channel.
6. Expect acknowledgement or record an evidence gap.

## Runtime Command

```bash
python -m long_horizon observer intervene --root . --goal-id <goal> --run-id <run> --observer-id <observer> --target-process-id <process> --message "<message>"
```
