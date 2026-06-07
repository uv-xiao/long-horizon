# V1 System Test Coverage

This note records what the system-test suite proves after hardening the v1
runtime tests.

## Covered End-To-End

- **Install and target-repo layout**: `.agents/` and `.long-horizon/` are created
  in a temporary target repository.
- **Goal/run lifecycle**: a contract becomes goal state, run state, board state,
  process metadata, reports, and ledgers.
- **Canonical logging**: typed JSONL ledgers receive sequence ids and loose logs
  do not advance transitions.
- **Workflow transitions**: artifact gates, check gates, human gates, wait gates,
  blocked transitions, and applied transitions are exercised.
- **Humanize v1-style nested loop**: plan acceptance, builder round, reviewer
  verdict, inner fork-join candidate exploration, observer steering, candidate
  import, human final acceptance, and completion.
- **Humanize v2-style workflow**: plan expansion, adversarial critique, plan
  acceptance gate, RLCR round, delta card, full alignment observer check,
  plan-amendment human gate, methodology report, and completion.
- **Process recovery**: interrupted executor session, regenerated brief,
  replacement session attach, and continuation.
- **Observer involvement**: observer sidecar process, multi-target observation,
  intervention request/delivery records, and no task-board mutation.
- **Human involvement**: pushed local comment envelopes are imported as typed
  human events and used for gate approvals.
- **Report playback**: `report-data.json` includes event-sequence playback,
  snapshots, lanes, process/workflow nodes, communication edges, comments,
  observer interventions, and stable anchors; `progress.html` renders a local
  slider/graph/lanes/inspector view.
- **CLI usability**: a subprocess-driven test exercises the public
  `python -m long_horizon` command path and generated report artifacts.

## Still Not Covered Or Deferred

- **Local report server**: `report serve` remains a TODO. The inbox/comment
  importer is covered first.
- **Real git worktree creation and merge**: tests represent parent/child process
  metadata and import events, but do not create real git worktrees or merge
  branches.
- **Cross-worktree copy-on-write state**: child process state is represented in
  one target repo runtime; full filesystem state copying across worktrees is not
  implemented in v1.
- **External channel adapters**: GitHub/Feishu/webhook delivery is not exercised;
  pushed local envelopes cover the normalized ingestion contract.
- **Artifact eviction/compression/externalization**: explicitly deferred.
- **Ledger repair**: hash-chain append behavior is covered; explicit repair
  tooling is not implemented.
- **Remote execution, benchmark, GPU, and task-specific evaluator adapters**:
  intentionally outside the default v1 runtime.
