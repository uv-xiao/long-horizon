---
name: analyze-target-agent
description: Detect target repository and agent capabilities before installing or starting long-horizon work.
---

# Analyze Target Agent

Read `.agents/templates/long-horizon/target-analysis.md` and follow its phases.

Use:

```bash
python -m long_horizon capabilities analyze --root . --target-agent auto
```

Outputs must include `.long-horizon/agent-capabilities.toml`,
`.long-horizon/agent-capabilities.md`, and
`.long-horizon/decisions/operation-mode.md`. Reuse cached analysis when the
fingerprint is fresh.
