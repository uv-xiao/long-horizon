from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVAL_ROOT = Path("/tmp/evals/long-horizon-calculator")
TARGET_NAME = "target-repo"
GOAL_ID = "calculator-eval"
RUN_ID = "run-1"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the external Codex calculator eval")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--eval-root", default=None, help="eval workspace root")
    common.add_argument("--template-repo", default=None, help="long-horizon template repo path")
    parser.add_argument("--eval-root", default=None, help="eval workspace root")
    parser.add_argument("--template-repo", default=None, help="long-horizon template repo path")
    sub = parser.add_subparsers(dest="cmd", required=True)

    prepare = sub.add_parser("prepare", parents=[common], help="create a fresh target git repo and prompt")
    prepare.add_argument("--reset", action="store_true")

    run = sub.add_parser("run", parents=[common], help="prepare, launch Codex, then verify")
    run.add_argument("--reset", action="store_true")
    run.add_argument("--model")
    run.add_argument("--no-verify", action="store_true")

    sub.add_parser("verify", parents=[common], help="verify the eval artifacts")
    sub.add_parser("clean", parents=[common], help="remove the eval root")

    args = parser.parse_args(argv)
    eval_root = Path(args.eval_root or DEFAULT_EVAL_ROOT).resolve()
    template_repo = Path(args.template_repo or REPO_ROOT).resolve()

    if args.cmd == "clean":
        clean(eval_root)
        return 0
    if args.cmd == "prepare":
        manifest = prepare_eval(eval_root, template_repo, reset=args.reset)
        print_json(manifest)
        return 0
    if args.cmd == "run":
        manifest = prepare_eval(eval_root, template_repo, reset=args.reset)
        result = run_codex_eval(eval_root, manifest, model=args.model)
        if not args.no_verify:
            verification = verify_eval(eval_root)
            print_json({"codex": result, "verification": verification})
            return 0 if verification["passed"] else 1
        print_json(result)
        return 0
    if args.cmd == "verify":
        result = verify_eval(eval_root)
        print_json(result)
        return 0 if result["passed"] else 1
    raise SystemExit("unknown command")


def prepare_eval(eval_root: Path, template_repo: Path, reset: bool = False) -> dict[str, Any]:
    if reset:
        clean(eval_root)
    target = eval_root / TARGET_NAME
    artifacts = eval_root / "artifacts"
    if target.exists():
        raise SystemExit(f"eval target already exists: {target}; rerun with --reset or clean first")
    artifacts.mkdir(parents=True, exist_ok=True)
    target.mkdir(parents=True, exist_ok=True)
    git(target, "init", "-b", "main")
    git(target, "config", "user.name", "Long Horizon Eval")
    git(target, "config", "user.email", "eval@example.invalid")
    write(target / "README.md", "# Calculator Eval Target\n")
    write(target / "TASK.md", task_text())
    write(target / ".gitignore", "__pycache__/\n*.pyc\n.long-horizon/\n")
    tests = target / "tests"
    tests.mkdir(parents=True, exist_ok=True)
    write(tests / "test_calculator.py", calculator_tests())
    git(target, "add", "README.md", "TASK.md", ".gitignore", "tests/test_calculator.py")
    git(target, "commit", "-m", "eval: seed calculator task")

    prompt = codex_prompt(template_repo)
    prompt_path = artifacts / "codex-prompt.md"
    write(prompt_path, prompt)
    manifest = {
        "eval": "calculator",
        "eval_root": str(eval_root),
        "target_repo": str(target),
        "template_repo": str(template_repo),
        "goal_id": GOAL_ID,
        "run_id": RUN_ID,
        "prompt": str(prompt_path),
        "codex_last_message": str(artifacts / "codex-last-message.md"),
        "codex_stdout": str(artifacts / "codex-stdout.jsonl"),
        "codex_command": codex_command(target, prompt_path, artifacts / "codex-last-message.md"),
        "verify_command": [sys.executable, str(Path(__file__).resolve()), "--eval-root", str(eval_root), "verify"],
        "review_artifacts": review_artifacts(target),
    }
    write_json(artifacts / "eval-manifest.json", manifest)
    return manifest


def run_codex_eval(eval_root: Path, manifest: dict[str, Any], model: str | None = None) -> dict[str, Any]:
    cmd = list(manifest["codex_command"])
    if model:
        cmd[2:2] = ["--model", model]
    stdout_path = Path(manifest["codex_stdout"])
    prompt = Path(manifest["prompt"]).read_text(encoding="utf-8")
    proc = subprocess.run(cmd, cwd=manifest["target_repo"], input=prompt, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    write(stdout_path, proc.stdout)
    write(eval_root / "artifacts" / "codex-stderr.txt", proc.stderr)
    result = {
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": str(stdout_path),
        "stderr": str(eval_root / "artifacts" / "codex-stderr.txt"),
        "last_message": manifest["codex_last_message"],
    }
    write_json(eval_root / "artifacts" / "codex-run.json", result)
    if proc.returncode != 0:
        return {**result, "status": "failed"}
    return {**result, "status": "completed"}


def verify_eval(eval_root: Path) -> dict[str, Any]:
    target = eval_root / TARGET_NAME
    report_data = target / ".long-horizon" / "goals" / GOAL_ID / "runs" / RUN_ID / "reports" / "report-data.json"
    checks: list[tuple[str, bool, str]] = []
    checks.append(("target repo is git repo", (target / ".git").exists(), str(target / ".git")))
    checks.append(("calculator.py exists", (target / "calculator.py").exists(), str(target / "calculator.py")))
    tests_passed = run_optional([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=target)
    checks.append(("calculator tests pass", tests_passed["returncode"] == 0, tests_passed["stdout"] + tests_passed["stderr"]))
    checks.append(("long-horizon installed", (target / ".agents").exists() and (target / ".long-horizon").exists(), str(target)))
    checks.append(("report-data.json exists", report_data.exists(), str(report_data)))
    data: dict[str, Any] = {}
    if report_data.exists():
        data = json.loads(report_data.read_text(encoding="utf-8"))
    mechanisms = data.get("mechanism_evidence", {})
    for key in ["evaluations", "notifications", "report_gui"]:
        checks.append((f"mechanism_evidence.{key}", bool(mechanisms.get(key, {}).get("events") or mechanisms.get(key, {}).get("artifacts")), key))
    checks.append(("observer intervention recorded", bool(data.get("observer_interventions")), "observer_interventions"))
    checks.append(("mailbox messages recorded", bool(data.get("mailbox_messages")), "mailbox_messages"))
    checks.append(("at least three processes", len(data.get("processes", [])) >= 3, str(len(data.get("processes", [])))))
    commits = run_optional(["git", "rev-list", "--count", "HEAD"], cwd=target)
    try:
        commit_count = int(commits["stdout"].strip())
    except ValueError:
        commit_count = 0
    checks.append(("final work committed", commit_count >= 2, commits["stdout"] + commits["stderr"]))

    failed = [name for name, ok, _detail in checks if not ok]
    result = {
        "eval": "calculator",
        "eval_root": str(eval_root),
        "target_repo": str(target),
        "passed": not failed,
        "failed_checks": failed,
        "checks": [{"name": name, "passed": ok, "detail": detail} for name, ok, detail in checks],
        "review_artifacts": review_artifacts(target),
    }
    write_json(eval_root / "artifacts" / "eval-result.json", result)
    return result


def clean(eval_root: Path) -> None:
    if eval_root.exists():
        shutil.rmtree(eval_root)


def codex_command(target: Path, prompt_path: Path, last_message_path: Path) -> list[str]:
    return [
        "codex",
        "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        "-C",
        str(target),
        "--output-last-message",
        str(last_message_path),
        "-",
    ]


def codex_prompt(template_repo: Path) -> str:
    lh = f"PYTHONPATH={template_repo} {sys.executable} -m long_horizon"
    return f"""# Calculator Eval For Long-Horizon Template

You are running inside a fresh target git repository created only for this eval.
You have yolo privileges for this target repo. Do not edit the template repo.

Task: read `TASK.md`, install the long-horizon template, use it to manage the
task, implement `calculator.py`, verify it, and leave human-reviewable evidence.

Use these exact ids:

- goal id: `{GOAL_ID}`
- run id: `{RUN_ID}`
- task id: `calculator-task`

Required commands and artifacts:

1. Install and initialize:

```bash
{lh} install --target . --apply --target-agent codex-goal
{lh} task setup --root . --request "Implement the calculator eval task" --task-id calculator-task --target-agent codex-goal
{lh} task initialize --root . --task-id calculator-task --goal-id {GOAL_ID} --run-id {RUN_ID}
```

2. Create at least these processes:

```bash
{lh} process create --root . --goal-id {GOAL_ID} --run-id {RUN_ID} --process-id candidate-simple --role candidate --process-kind workspace
{lh} process create --root . --goal-id {GOAL_ID} --run-id {RUN_ID} --process-id candidate-safe --role candidate --process-kind workspace
{lh} observer create --root . --goal-id {GOAL_ID} --run-id {RUN_ID} --process-id calculator-observer --observe-target primary --observe-target candidate-simple --observe-target candidate-safe
```

3. Use mailbox communication and observer steering:

```bash
{lh} mailbox send --root . --goal-id {GOAL_ID} --run-id {RUN_ID} --source-process-id primary --target-process-id candidate-simple --message-type implementation_request --body "create the shortest passing calculator"
{lh} observer intervene --root . --goal-id {GOAL_ID} --run-id {RUN_ID} --observer-id calculator-observer --target-process-id primary --message "verify with the fixed unittest suite before completion"
{lh} notify --root . --goal-id {GOAL_ID} --run-id {RUN_ID} --channel local --subject "Calculator eval review" --body "Inspect report-data.json and progress.html"
```

4. Implement `calculator.py` so this command passes:

```bash
{sys.executable} -m unittest discover -s tests
```

5. Record runtime evidence:

```bash
{lh} evaluation run --root . --goal-id {GOAL_ID} --run-id {RUN_ID} --eval-id calculator-unittest --adapter command --command "{sys.executable} -m unittest discover -s tests"
{lh} report-gui --root . --goal-id {GOAL_ID} --run-id {RUN_ID}
{lh} report generate --root . --goal-id {GOAL_ID} --run-id {RUN_ID}
```

6. Commit the final target repo changes.

Acceptance:

- `calculator.py` exists and passes `python -m unittest discover -s tests`.
- `.long-horizon/goals/{GOAL_ID}/runs/{RUN_ID}/reports/report-data.json`
  exists and includes `mechanism_evidence`.
- Report data includes at least three processes, mailbox messages, observer
  interventions, evaluation evidence, notification evidence, and report GUI
  evidence.
- The final target repo has at least two commits.

Final response: summarize the implemented calculator, tests run, report paths,
and commit hash.
"""


def task_text() -> str:
    return """# Calculator Eval Task

Implement `calculator.py`.

The program must:

- read one arithmetic expression from stdin;
- print one numeric result to stdout;
- support `+`, `-`, `*`, `/`, exponentiation, parentheses, decimals, and unary
  minus for the fixed eval cases;
- reject names, imports, function calls, attributes, and other Python execution
  surfaces;
- pass `python -m unittest discover -s tests`.

This target repo is intentionally separate from the template repository. The
long-horizon template must be installed and used inside this target repo.
"""


def calculator_tests() -> str:
    return '''from __future__ import annotations

import subprocess
import sys
import unittest


class CalculatorEvalTests(unittest.TestCase):
    def run_calc(self, expression: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "calculator.py"],
            input=expression + "\\n",
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
        )

    def assert_value(self, expression: str, expected: float) -> None:
        proc = self.run_calc(expression)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertAlmostEqual(float(proc.stdout.strip()), expected)

    def test_operator_precedence(self):
        self.assert_value("1+2*3", 7.0)

    def test_parentheses_and_division(self):
        self.assert_value("(8-3)/5", 1.0)

    def test_power_and_addition(self):
        self.assert_value("2**3+4", 12.0)

    def test_decimal_and_unary_minus(self):
        self.assert_value("-3.5 + 10/4", -1.0)

    def test_rejects_code_execution(self):
        proc = self.run_calc("__import__('os').system('echo bad')")
        self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
'''


def review_artifacts(target: Path) -> dict[str, str]:
    run = target / ".long-horizon" / "goals" / GOAL_ID / "runs" / RUN_ID
    return {
        "target_repo": str(target),
        "task": str(target / "TASK.md"),
        "calculator": str(target / "calculator.py"),
        "report_html": str(run / "reports" / "progress.html"),
        "report_data": str(run / "reports" / "report-data.json"),
        "logs": str(run / "logs"),
        "processes": str(run / "processes"),
    }


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: dict[str, Any]) -> None:
    write(path, json.dumps(data, indent=2, sort_keys=True) + "\n")


def print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def run_optional(cmd: list[str], cwd: Path) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


def git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {cwd}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    return proc.stdout


if __name__ == "__main__":
    raise SystemExit(main())
