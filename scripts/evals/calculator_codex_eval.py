from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVAL_ROOT = REPO_ROOT / "tmp" / "evals" / "long-horizon-calculator"
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
    git(target, "init", "-b", "main", eval_root=eval_root, process_id="prepare-git-001-init")
    git(target, "config", "user.name", "Long Horizon Eval", eval_root=eval_root, process_id="prepare-git-002-config-name")
    git(target, "config", "user.email", "eval@example.invalid", eval_root=eval_root, process_id="prepare-git-003-config-email")
    write(target / "README.md", "# Calculator Eval Target\n")
    write(target / "TASK.md", task_text())
    write(target / ".gitignore", "__pycache__/\n*.pyc\n.long-horizon/\n")
    tests = target / "tests"
    tests.mkdir(parents=True, exist_ok=True)
    write(tests / "test_calculator.py", calculator_tests())
    git(target, "add", "README.md", "TASK.md", ".gitignore", "tests/test_calculator.py", eval_root=eval_root, process_id="prepare-git-004-add")
    git(target, "commit", "-m", "eval: seed calculator task", eval_root=eval_root, process_id="prepare-git-005-commit")

    prompt = codex_prompt(template_repo)
    codex_logs = process_log_paths(artifacts, "codex-main", prompt=True, last_message=True)
    prompt_path = Path(codex_logs["prompt"])
    write(prompt_path, prompt)
    process_logs = collect_process_logs(artifacts)
    process_logs["codex-main"] = codex_logs
    manifest = {
        "eval": "calculator",
        "eval_root": str(eval_root),
        "target_repo": str(target),
        "template_repo": str(template_repo),
        "goal_id": GOAL_ID,
        "run_id": RUN_ID,
        "prompt": str(prompt_path),
        "process_logs": process_logs,
        "codex_last_message": codex_logs["last_message"],
        "codex_stdout": codex_logs["stdout"],
        "codex_command": codex_command(target, prompt_path, Path(codex_logs["last_message"])),
        "verify_command": [sys.executable, str(Path(__file__).resolve()), "--eval-root", str(eval_root), "verify"],
        "review_artifacts": review_artifacts(target),
    }
    write_json(artifacts / "eval-manifest.json", manifest)
    return manifest


def run_codex_eval(eval_root: Path, manifest: dict[str, Any], model: str | None = None) -> dict[str, Any]:
    cmd = list(manifest["codex_command"])
    if model:
        cmd[2:2] = ["--model", model]
    prompt = Path(manifest["prompt"]).read_text(encoding="utf-8")
    result = run_captured_process(
        eval_root,
        "codex-main",
        cmd,
        cwd=Path(manifest["target_repo"]),
        input_text=prompt,
        stdin_ref=manifest["prompt"],
        extra={"last_message": manifest["codex_last_message"]},
    )
    public_result = {key: value for key, value in result.items() if key not in {"stdout_text", "stderr_text"}}
    if result["returncode"] != 0:
        return {**public_result, "status": "failed"}
    return {**public_result, "status": "completed"}


def verify_eval(eval_root: Path) -> dict[str, Any]:
    target = eval_root / TARGET_NAME
    manifest_path = eval_root / "artifacts" / "eval-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    report_data = target / ".long-horizon" / "goals" / GOAL_ID / "runs" / RUN_ID / "reports" / "report-data.json"
    run_path = target / ".long-horizon" / "goals" / GOAL_ID / "runs" / RUN_ID
    checks: list[tuple[str, bool, str]] = []
    checks.append(("target repo is git repo", (target / ".git").exists(), str(target / ".git")))
    checks.append(("calculator.py exists", (target / "calculator.py").exists(), str(target / "calculator.py")))
    tests_passed = run_captured_process(eval_root, "verify-unittest", [sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=target)
    checks.append(("calculator tests pass", tests_passed["returncode"] == 0, tests_passed["stdout_text"] + tests_passed["stderr_text"]))
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
    process_ids = [str(process.get("process_id", "")) for process in data.get("processes", []) if process.get("process_id")]
    chat_dir = run_path / "artifacts" / "process-chats"
    missing_chats = [process_id for process_id in process_ids if not (chat_dir / f"{process_id}.md").exists()]
    checks.append(
        (
            "process chat artifacts for all processes",
            bool(process_ids) and not missing_chats,
            f"processes={process_ids}; missing={missing_chats}; chat_dir={chat_dir}",
        )
    )
    commits = run_captured_process(eval_root, "verify-git-rev-list", ["git", "rev-list", "--count", "HEAD"], cwd=target)
    try:
        commit_count = int(str(commits["stdout_text"]).strip())
    except ValueError:
        commit_count = 0
    checks.append(("final work committed", commit_count >= 2, commits["stdout_text"] + commits["stderr_text"]))
    process_logs = {**manifest.get("process_logs", {}), **collect_process_logs(eval_root / "artifacts")}
    for process_id, paths in sorted(process_logs.items()):
        checks.append((f"{process_id} command captured", Path(paths.get("command", "")).exists(), paths.get("command", "")))
        checks.append((f"{process_id} stdout captured", Path(paths.get("stdout", "")).exists(), paths.get("stdout", "")))
        checks.append((f"{process_id} stderr captured", Path(paths.get("stderr", "")).exists(), paths.get("stderr", "")))
        checks.append((f"{process_id} run metadata captured", Path(paths.get("run_metadata", "")).exists(), paths.get("run_metadata", "")))
        if "prompt" in paths:
            checks.append((f"{process_id} prompt captured", Path(paths["prompt"]).exists(), paths["prompt"]))
        if "last_message" in paths:
            checks.append((f"{process_id} last message captured", Path(paths["last_message"]).exists(), paths["last_message"]))

    failed = [name for name, ok, _detail in checks if not ok]
    result = {
        "eval": "calculator",
        "eval_root": str(eval_root),
        "target_repo": str(target),
        "passed": not failed,
        "failed_checks": failed,
        "checks": [{"name": name, "passed": ok, "detail": detail} for name, ok, detail in checks],
        "review_artifacts": review_artifacts(target),
        "process_logs": process_logs,
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


def process_log_paths(artifacts: Path, process_id: str, prompt: bool = False, last_message: bool = False) -> dict[str, str]:
    base = artifacts / "process-logs" / process_id
    paths = {
        "prompt": str(base / "prompt.md"),
        "command": str(base / "command.json"),
        "stdout": str(base / "stdout.jsonl"),
        "stderr": str(base / "stderr.txt"),
        "run_metadata": str(base / "run.json"),
        "last_message": str(base / "last-message.md"),
    }
    if not prompt:
        paths.pop("prompt")
    if not last_message:
        paths.pop("last_message")
    return paths


def collect_process_logs(artifacts: Path) -> dict[str, dict[str, str]]:
    base = artifacts / "process-logs"
    if not base.exists():
        return {}
    logs: dict[str, dict[str, str]] = {}
    for process_dir in sorted(path for path in base.iterdir() if path.is_dir()):
        paths = process_log_paths(artifacts, process_dir.name)
        if (process_dir / "prompt.md").exists():
            paths["prompt"] = str(process_dir / "prompt.md")
        if (process_dir / "last-message.md").exists():
            paths["last_message"] = str(process_dir / "last-message.md")
        logs[process_dir.name] = paths
    return logs


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

5. Record per-process chat/transcript artifacts for every modeled process.
   This eval uses fixed fake process IO, but the evidence must still exist so a
   reviewer can inspect what each process was asked to do and what it reported.

```bash
python - <<'PY'
from pathlib import Path

run = Path(".long-horizon/goals/{GOAL_ID}/runs/{RUN_ID}")
chat_dir = run / "artifacts" / "process-chats"
chat_dir.mkdir(parents=True, exist_ok=True)
transcripts = {{
    "primary": '''# primary chat

Input: install the long-horizon template, coordinate candidates, implement the accepted calculator, run evals, generate reports, and commit.
Output: selected the safe AST-based implementation after fixed candidate review and unittest evidence.
''',
    "candidate-simple": '''# candidate-simple chat

Input: create the shortest passing calculator.
Output: proposed a minimal evaluator; rejected because the task requires explicit rejection of Python execution surfaces.
''',
    "candidate-safe": '''# candidate-safe chat

Input: create a safe calculator for the fixed tests.
Output: proposed AST whitelisting for arithmetic expressions and rejection of calls, names, attributes, imports, and code execution.
''',
    "calculator-observer": '''# calculator-observer chat

Input: observe primary and both candidate processes.
Output: steered primary to verify with the fixed unittest suite before completion.
''',
    "notify-local": '''# notify-local chat

Input: record the local notification requested by the primary process.
Output: wrote the local notification artifact and exposed it through report mechanism evidence.
''',
}}
for process_id, body in transcripts.items():
    (chat_dir / f"{{process_id}}.md").write_text(body, encoding="utf-8")
PY
{lh} log append --root . --goal-id {GOAL_ID} --run-id {RUN_ID} --ledger artifacts --event-type process_chat_captured --process-id primary --payload '{{"process_id":"primary","artifact":"artifacts/process-chats/primary.md","capture_kind":"fixed-eval-chat"}}'
{lh} log append --root . --goal-id {GOAL_ID} --run-id {RUN_ID} --ledger artifacts --event-type process_chat_captured --process-id candidate-simple --payload '{{"process_id":"candidate-simple","artifact":"artifacts/process-chats/candidate-simple.md","capture_kind":"fixed-eval-chat"}}'
{lh} log append --root . --goal-id {GOAL_ID} --run-id {RUN_ID} --ledger artifacts --event-type process_chat_captured --process-id candidate-safe --payload '{{"process_id":"candidate-safe","artifact":"artifacts/process-chats/candidate-safe.md","capture_kind":"fixed-eval-chat"}}'
{lh} log append --root . --goal-id {GOAL_ID} --run-id {RUN_ID} --ledger artifacts --event-type process_chat_captured --process-id calculator-observer --payload '{{"process_id":"calculator-observer","artifact":"artifacts/process-chats/calculator-observer.md","capture_kind":"fixed-eval-chat"}}'
{lh} log append --root . --goal-id {GOAL_ID} --run-id {RUN_ID} --ledger artifacts --event-type process_chat_captured --process-id notify-local --payload '{{"process_id":"notify-local","artifact":"artifacts/process-chats/notify-local.md","capture_kind":"fixed-eval-chat"}}'
```

6. Record runtime evidence:

```bash
{lh} evaluation run --root . --goal-id {GOAL_ID} --run-id {RUN_ID} --eval-id calculator-unittest --adapter command --command "{sys.executable} -m unittest discover -s tests"
{lh} report-gui --root . --goal-id {GOAL_ID} --run-id {RUN_ID}
{lh} report generate --root . --goal-id {GOAL_ID} --run-id {RUN_ID}
```

7. Commit the final target repo changes.

Acceptance:

- `calculator.py` exists and passes `python -m unittest discover -s tests`.
- `.long-horizon/goals/{GOAL_ID}/runs/{RUN_ID}/reports/report-data.json`
  exists and includes `mechanism_evidence`.
- Report data includes at least three processes, mailbox messages, observer
  interventions, evaluation evidence, notification evidence, and report GUI
  evidence.
- Every process in report data has a matching markdown transcript under
  `.long-horizon/goals/{GOAL_ID}/runs/{RUN_ID}/artifacts/process-chats/`.
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


def run_captured_process(
    eval_root: Path,
    process_id: str,
    cmd: list[str],
    cwd: Path,
    input_text: str | None = None,
    stdin_ref: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifacts = eval_root / "artifacts"
    paths = process_log_paths(artifacts, process_id)
    command_record = {"process_id": process_id, "command": cmd, "cwd": str(cwd)}
    if stdin_ref:
        command_record["stdin"] = stdin_ref
    write_json(Path(paths["command"]), command_record)
    proc = subprocess.run(cmd, cwd=cwd, input=input_text, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    write(Path(paths["stdout"]), proc.stdout)
    write(Path(paths["stderr"]), proc.stderr)
    result: dict[str, Any] = {
        "process_id": process_id,
        "command": cmd,
        "cwd": str(cwd),
        "returncode": proc.returncode,
        "stdout": paths["stdout"],
        "stderr": paths["stderr"],
    }
    if extra:
        result.update(extra)
    write_json(Path(paths["run_metadata"]), result)
    return {**result, "stdout_text": proc.stdout, "stderr_text": proc.stderr}


def git(cwd: Path, *args: str, eval_root: Path, process_id: str) -> str:
    result = run_captured_process(eval_root, process_id, ["git", *args], cwd=cwd)
    if result["returncode"] != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {cwd}\nSTDOUT:\n{result['stdout_text']}\nSTDERR:\n{result['stderr_text']}")
    return str(result["stdout_text"])


if __name__ == "__main__":
    raise SystemExit(main())
