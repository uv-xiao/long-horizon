# TODO

- Define post-run adapter promotion. Runs may learn and immediately use missing adapters while logging them under run artifacts; a later mechanism should promote stable learned adapters into reusable memory or skills after review.
- Add an artifact retention and eviction mechanism. Evidence artifacts should be append-only for auditability, but the system needs a policy for pruning, archiving, compressing, or externalizing large raw artifacts while preserving lineage and completion-audit trust.
- Add git merge conflict remediation policy. V1 can merge a clean child branch into the parent and logs failed merges, but it does not yet guide conflict resolution, rollback, or retry strategy.
- Add explicit ledger repair/reconciliation tooling. V1 writes hash-chained append-only ledgers, but repairing corrupted or partially copied ledgers remains future work.
