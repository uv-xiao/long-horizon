---
name: install-long-horizon
description: Produce and apply a mode-aware long-horizon install plan.
---

# Install Long-Horizon

Read `.agents/templates/long-horizon/install-plan.md` and inspect the cached
capability analysis first.

Use dry-run planning before applying:

```bash
python -m long_horizon install --target . --target-agent auto
python -m long_horizon install --target . --target-agent auto --apply
```

Native-agent mode must enable or document native features instead of installing
a competing loop. Runtime-owned mode must install the full runtime evidence
surface.
