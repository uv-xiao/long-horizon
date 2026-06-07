# TODO

- Define post-run adapter promotion. Runs may learn and immediately use missing adapters while logging them under run artifacts; a later mechanism should promote stable learned adapters into reusable memory or skills after review.
- Add an artifact retention and eviction mechanism. Evidence artifacts should be append-only for auditability, but the system needs a policy for pruning, archiving, compressing, or externalizing large raw artifacts while preserving lineage and completion-audit trust.
- Add `python -m long_horizon report serve` as a local helper server. V1 implements the push inbox format and comment importer first; the server should later serve the latest report, accept comment POSTs, and support polling-first live updates without becoming the workflow runtime.
