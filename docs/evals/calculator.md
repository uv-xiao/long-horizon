# Calculator Eval

The calculator eval starts from a fresh git repo under
repo-local `./tmp/evals/long-horizon-calculator`. A new Codex session is then
launched inside that target repo with yolo privileges:

```bash
python scripts/evals/calculator_codex_eval.py run --reset
```

The generated command uses:

```bash
codex exec --dangerously-bypass-approvals-and-sandbox -C ./tmp/evals/long-horizon-calculator ...
```

## What Codex Must Do

The prompt instructs Codex to:

1. install the long-horizon template into the target repo;
2. run task setup and initialization with goal id `calculator-eval` and run id
   `run-1`;
3. create candidate and observer processes;
4. route mailbox messages and observer intervention evidence;
5. write per-process chat artifacts under `artifacts/process-chats`;
6. implement `calculator.py`;
7. run the fixed unittest suite through the evaluation adapter;
8. create notification and report GUI evidence;
9. generate `progress.html`, `progress.md`, and `report-data.json`;
10. commit the final target repo changes.

## Verify

Run verification independently:

```bash
python scripts/evals/calculator_codex_eval.py verify
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
- each modeled process has a markdown transcript under
  `.long-horizon/goals/calculator-eval/runs/run-1/artifacts/process-chats/`;
- the external Codex process has captured prompt, command, stdout, stderr, run
  metadata, and last-message artifacts under `processes/codex-main/logs`;
- prepare-time and verify-time subprocesses have captured command, stdout,
  stderr, and run metadata under `processes/<process-id>/logs/`;
- the target repo has a final commit after the seed commit.

## Human Review Artifacts

Inspect:

```text
./tmp/evals/long-horizon-calculator/.long-horizon/goals/calculator-eval/runs/run-1/eval-manifest.json
./tmp/evals/long-horizon-calculator/.long-horizon/goals/calculator-eval/runs/run-1/eval-result.json
./tmp/evals/long-horizon-calculator/.long-horizon/goals/calculator-eval/runs/run-1/processes/codex-main/logs/prompt.md
./tmp/evals/long-horizon-calculator/.long-horizon/goals/calculator-eval/runs/run-1/processes/codex-main/logs/command.json
./tmp/evals/long-horizon-calculator/.long-horizon/goals/calculator-eval/runs/run-1/processes/codex-main/logs/stdout.jsonl
./tmp/evals/long-horizon-calculator/.long-horizon/goals/calculator-eval/runs/run-1/processes/codex-main/logs/stderr.txt
./tmp/evals/long-horizon-calculator/.long-horizon/goals/calculator-eval/runs/run-1/processes/codex-main/logs/run.json
./tmp/evals/long-horizon-calculator/.long-horizon/goals/calculator-eval/runs/run-1/processes/codex-main/logs/last-message.md
./tmp/evals/long-horizon-calculator/.long-horizon/goals/calculator-eval/runs/run-1/processes/prepare-git-001-init/logs/
./tmp/evals/long-horizon-calculator/.long-horizon/goals/calculator-eval/runs/run-1/processes/verify-unittest/logs/
./tmp/evals/long-horizon-calculator/.long-horizon/goals/calculator-eval/runs/run-1/processes/verify-git-rev-list/logs/
./tmp/evals/long-horizon-calculator/calculator.py
./tmp/evals/long-horizon-calculator/.long-horizon/goals/calculator-eval/runs/run-1/artifacts/process-chats/
./tmp/evals/long-horizon-calculator/.long-horizon/goals/calculator-eval/runs/run-1/reports/progress.html
./tmp/evals/long-horizon-calculator/.long-horizon/goals/calculator-eval/runs/run-1/reports/report-data.json
```

## Clean

```bash
python scripts/evals/calculator_codex_eval.py clean
```
