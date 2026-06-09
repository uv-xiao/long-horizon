---
name: promote-adapter
description: Promote a learned adapter or command bridge after a run proves it useful.
---

# Promote Adapter

Use this when a run learns how to operate a tool, benchmark, remote executor, or
service adapter.

## Workflow

1. Read adapter usage logs and artifacts.
2. Verify the adapter worked at least once and record known failure modes.
3. Write the adapter template or skill in the configured `.agents/` location.
4. Keep secrets/auth out of the adapter body.
5. Record deposition review evidence with validation and rollback.
