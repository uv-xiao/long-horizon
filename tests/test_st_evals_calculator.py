from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "evals" / "calculator_codex_eval.py"
GOAL_RUN = Path(".long-horizon") / "goals" / "calculator-eval" / "runs" / "run-1"


class CalculatorCodexEvalHarnessTests(unittest.TestCase):
    def test_prepare_creates_real_git_repo_prompt_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            eval_root = Path(tmp) / "calculator"
            self.run_script("prepare", "--eval-root", str(eval_root), "--reset")

            target = eval_root
            manifest = json.loads((eval_root / GOAL_RUN / "eval-manifest.json").read_text(encoding="utf-8"))
            prompt = Path(manifest["prompt"]).read_text(encoding="utf-8")

            self.assertTrue((target / ".git").exists())
            self.assertFalse((eval_root / "target-repo").exists())
            self.assertFalse((eval_root / "artifacts").exists())
            self.assertTrue((target / "TASK.md").exists())
            self.assertTrue((target / "tests" / "test_calculator.py").exists())
            self.assertEqual(self.git(target, "rev-list", "--count", "HEAD").strip(), "1")
            self.assertEqual(manifest["target_repo"], str(target))
            self.assertIn("--dangerously-bypass-approvals-and-sandbox", " ".join(manifest["codex_command"]))
            self.assertEqual(manifest["codex_command"][-1], "-")
            self.assertIn("codex-main", manifest["process_logs"])
            codex_log = manifest["process_logs"]["codex-main"]
            self.assertEqual(codex_log["prompt"], str(eval_root / GOAL_RUN / "processes" / "codex-main" / "logs" / "prompt.md"))
            self.assertTrue((eval_root / GOAL_RUN / "processes" / "codex-main" / "logs" / "prompt.md").exists())
            self.assertIn("python -m long_horizon install", prompt)
            self.assertIn("calculator-eval", prompt)
            self.assertIn("mechanism_evidence", prompt)
            self.assertIn("artifacts/process-chats", prompt)

    def test_verify_rejects_prepared_but_unrun_eval(self):
        with tempfile.TemporaryDirectory() as tmp:
            eval_root = Path(tmp) / "calculator"
            self.run_script("prepare", "--eval-root", str(eval_root), "--reset")
            proc = self.run_script("verify", "--eval-root", str(eval_root), check=False)
            self.assertNotEqual(proc.returncode, 0)
            result = json.loads((eval_root / GOAL_RUN / "eval-result.json").read_text(encoding="utf-8"))
            self.assertFalse(result["passed"])
            self.assertIn("calculator.py exists", result["failed_checks"])
            self.assertIn("report-data.json exists", result["failed_checks"])
            self.assertIn("codex-main stdout captured", result["failed_checks"])
            self.assertIn("process chat artifacts for all processes", result["failed_checks"])
            self.assertIn("prepare-git-001-init", result["process_logs"])
            self.assertIn("verify-unittest", result["process_logs"])
            self.assertIn("verify-git-rev-list", result["process_logs"])

    def test_eval_docs_define_external_codex_run_and_review_artifacts(self):
        repo = Path(__file__).resolve().parents[1]
        readme = (repo / "docs" / "evals" / "README.md").read_text(encoding="utf-8")
        calculator = (repo / "docs" / "evals" / "calculator.md").read_text(encoding="utf-8")
        combined = readme + calculator
        self.assertIn("./tmp/evals", combined)
        self.assertNotIn(" `/tmp/evals", combined)
        self.assertNotIn(" /tmp/evals", combined)
        self.assertIn("codex exec", combined)
        self.assertIn("--dangerously-bypass-approvals-and-sandbox", combined)
        self.assertIn("scripts/evals/calculator_codex_eval.py", combined)
        self.assertIn("processes/codex-main/logs", combined)
        self.assertIn("artifacts/process-chats", combined)
        self.assertNotIn("/target-repo", combined)
        self.assertNotIn("<name>/target-repo", combined)
        self.assertNotIn("/artifacts/process-logs", combined)
        self.assertIn("report-data.json", combined)

    def run_script(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if check and proc.returncode != 0:
            raise AssertionError(f"script failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
        return proc

    def git(self, cwd: Path, *args: str) -> str:
        proc = subprocess.run(["git", *args], cwd=cwd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return proc.stdout


if __name__ == "__main__":
    unittest.main()
