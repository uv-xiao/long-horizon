---
name: operate-long-horizon-process
description: Handle checkpoints, observer interventions, fork/join, recovery, and active-run policy changes.
---

# Operate Long-Horizon Process

Use these prompt templates as needed:

- `.agents/templates/long-horizon/observer-intervention.md`
- `.agents/templates/long-horizon/join-decision.md`
- `.agents/templates/long-horizon/execution-brief.md`

Do not mutate workflow boards directly. Observer steering is append-only and
parent joins must cite child evidence before advancement.
