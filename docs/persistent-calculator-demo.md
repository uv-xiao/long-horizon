# Persistent Calculator Demo

This demo creates a human-inspectable long-horizon run that stays on disk after
the test finishes. It is intentionally separate from the automated `tempfile`
system tests.

The demo task is:

> Write the shortest passing expression calculator. The program reads one
> expression string from stdin and prints the numeric value.

The demo follows a Humanize v1-style loop:

1. Human plan acceptance gate.
2. Inner candidate loop with at least three iterations.
3. Three child worktrees try different languages.
4. A watchdog observer records steering interventions.
5. Parent imports child artifacts and evaluations.
6. Parent selects the shortest passing candidate.
7. Parent merges the selected child branch.
8. Final human acceptance gate.
9. The canonical timeline report is generated for human inspection.

## Run

From the implementation branch:

```bash
python scripts/persistent_calculator_demo.py run --reset --use-codex
```

Default persistent location:

```text
../long-horizon-calculator-demo/
```

Persistent branches:

```text
lh/demo/calculator-parent
lh/demo/calculator-python
lh/demo/calculator-node
lh/demo/calculator-perl
```

The `--use-codex` flag makes each child worktree invoke `codex exec` to write
its candidate calculator source file. Without that flag, the demo uses a
deterministic fallback for debugging the workflow mechanics.

## Inspect

Print the current paths and summary:

```bash
python scripts/persistent_calculator_demo.py status
```

Open these generated files in the parent worktree:

```text
../long-horizon-calculator-demo/parent/.long-horizon/goals/calculator-shortest/runs/run-1/reports/progress.html
../long-horizon-calculator-demo/parent/.long-horizon/goals/calculator-shortest/runs/run-1/reports/report-data.json
../long-horizon-calculator-demo/parent/.long-horizon/goals/calculator-shortest/runs/run-1/artifacts/selection/selected-candidate.json
../long-horizon-calculator-demo/parent/.long-horizon/goals/calculator-shortest/runs/run-1/artifacts/process-merges/
../long-horizon-calculator-demo/parent/.long-horizon/goals/calculator-shortest/runs/run-1/logs/
```

Inspect child worktrees:

```text
../long-horizon-calculator-demo/worktrees/candidate-python/
../long-horizon-calculator-demo/worktrees/candidate-node/
../long-horizon-calculator-demo/worktrees/candidate-perl/
```

Each child has its own copied `.long-horizon/` state and candidate artifacts.

## Workflow Merge Specification

The demo flow declares a merge strategy in `flow.snapshot.toml`:

```toml
[[merge_strategies]]
id = "shortest_passing_calculator"
from_state = "merge_selection"
candidate_processes = [
  "candidate-python",
  "candidate-node",
  "candidate-perl",
]
selection_metric = "fewest_source_bytes_after_fixed_expression_tests"
repository_strategy = "merge_child_branch_no_ff"
workflow_imports = [
  "candidate_summary",
  "evaluation",
  "adapter_note",
  "process_merge_artifact",
]
required_checks = ["selected_candidate_tests_passed"]
promotion_policy = "parent_selects_shortest_passing_candidate"
rejection_policy = "import compact summaries; leave full failed artifacts in child state"
```

This records the merge policy as part of the workflow snapshot. The runtime
executes the repository part through `process merge-child-branch` and records
the workflow part as parent-side merge artifacts under:

```text
artifacts/process-merges/
```

## Clean

Remove persistent demo worktrees and branches:

```bash
python scripts/persistent_calculator_demo.py clean
```

Equivalent manual cleanup:

```bash
git worktree remove --force ../long-horizon-calculator-demo/worktrees/candidate-python
git worktree remove --force ../long-horizon-calculator-demo/worktrees/candidate-node
git worktree remove --force ../long-horizon-calculator-demo/worktrees/candidate-perl
git worktree remove --force ../long-horizon-calculator-demo/parent
git worktree prune
git branch -D lh/demo/calculator-python
git branch -D lh/demo/calculator-node
git branch -D lh/demo/calculator-perl
git branch -D lh/demo/calculator-parent
rm -rf ../long-horizon-calculator-demo
```
