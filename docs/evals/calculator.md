# Calculator Eval

The calculator eval starts from a fresh git repo under
`/tmp/evals/long-horizon-calculator/target-repo`. A new Codex session is then
launched inside that target repo with yolo privileges:

```bash
python scripts/evals/calculator_codex_eval.py --eval-root /tmp/evals/long-horizon-calculator run --reset
```

The generated command uses:

```bash
codex exec --dangerously-bypass-approvals-and-sandbox -C /tmp/evals/long-horizon-calculator/target-repo ...
```

## What Codex Must Do

The prompt instructs Codex to:

1. install the long-horizon template into the target repo;
2. run task setup and initialization with goal id `calculator-eval` and run id
   `run-1`;
3. create candidate and observer processes;
4. route mailbox messages and observer intervention evidence;
5. implement `calculator.py`;
6. run the fixed unittest suite through the evaluation adapter;
7. create notification and report GUI evidence;
8. generate `progress.html`, `progress.md`, and `report-data.json`;
9. commit the final target repo changes.

## Verify

Run verification independently:

```bash
python scripts/evals/calculator_codex_eval.py --eval-root /tmp/evals/long-horizon-calculator verify
```

The verifier checks:

- the target is a real git repo;
- `calculator.py` exists;
- `python -m unittest discover -s tests` passes in the target repo;
- the long-horizon template is installed in the target repo;
- `report-data.json` exists;
- `report-data.json` contains `mechanism_evidence` for evaluations,
  notifications, and report GUI;
- observer interventions, mailbox messages, and at least three processes are
  present;
- the target repo has a final commit after the seed commit.

## Human Review Artifacts

Inspect:

```text
/tmp/evals/long-horizon-calculator/artifacts/eval-manifest.json
/tmp/evals/long-horizon-calculator/artifacts/codex-prompt.md
/tmp/evals/long-horizon-calculator/artifacts/codex-last-message.md
/tmp/evals/long-horizon-calculator/artifacts/eval-result.json
/tmp/evals/long-horizon-calculator/target-repo/calculator.py
/tmp/evals/long-horizon-calculator/target-repo/.long-horizon/goals/calculator-eval/runs/run-1/reports/progress.html
/tmp/evals/long-horizon-calculator/target-repo/.long-horizon/goals/calculator-eval/runs/run-1/reports/report-data.json
```

## Clean

```bash
python scripts/evals/calculator_codex_eval.py --eval-root /tmp/evals/long-horizon-calculator clean
```
