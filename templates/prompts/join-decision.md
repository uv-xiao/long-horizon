# Join Decision Prompt

## Hard Constraints

- Parent processes may inspect child process state and import selected results.
- Do not rewrite child `.long-horizon/` state in place.
- Candidate selection must cite evidence and eval results.

## Sequential Phases

1. Read flow-declared wait/join gates.
2. Inspect each child process status, artifacts, checks, and observer notes.
3. Determine whether quorum and terminal-state conditions are satisfied.
4. Compare candidates against acceptance criteria and merge-quality evals.
5. Import selected child artifacts with provenance.
6. Merge child branch only when clean or start a merge-repair workflow.
7. Record rejected/cancelled child learning summaries when useful.

## Review Gate

The parent cannot advance until wait conditions and candidate selection evidence
are both explicit.
