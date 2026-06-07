from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliReportSystemTest(unittest.TestCase):
    def test_cli_driven_agent_mimic_generates_complete_playback_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_cli("install", "--target", str(root), "--apply")
            contract = root / "contract.md"
            contract.write_text("# CLI fixed agent mimic\n", encoding="utf-8")
            self.run_cli("goal", "create", "--root", str(root), "--goal-id", "goal-cli", "--contract", str(contract))
            self.run_cli("run", "create", "--root", str(root), "--goal-id", "goal-cli", "--run-id", "run-1")
            run = root / ".long-horizon" / "goals" / "goal-cli" / "runs" / "run-1"

            blocked = self.run_cli("transition", "--root", str(root), "--goal-id", "goal-cli", "--run-id", "run-1", "--process-id", "primary", "--to", "implement")
            self.assertEqual(blocked["status"], "blocked")

            plan = run / "artifacts" / "plan.md"
            plan.parent.mkdir(parents=True, exist_ok=True)
            plan.write_text("fixed agent plan output\n", encoding="utf-8")
            self.assertEqual(
                self.run_cli("transition", "--root", str(root), "--goal-id", "goal-cli", "--run-id", "run-1", "--process-id", "primary", "--to", "implement")["status"],
                "applied",
            )
            self.run_cli(
                "log",
                "append",
                "--root",
                str(root),
                "--goal-id",
                "goal-cli",
                "--run-id",
                "run-1",
                "--ledger",
                "commands",
                "--event-type",
                "check_result",
                "--payload",
                '{"check_id":"tests_passed","status":"passed"}',
            )
            self.assertEqual(
                self.run_cli("transition", "--root", str(root), "--goal-id", "goal-cli", "--run-id", "run-1", "--process-id", "primary", "--to", "review")["status"],
                "applied",
            )
            report = self.run_cli("report", "generate", "--root", str(root), "--goal-id", "goal-cli", "--run-id", "run-1")
            self.assertEqual(report["playback"]["axis"], "event_sequence")
            self.assertIn("transition", report["event_lanes"])
            self.assertTrue((run / "reports" / "progress.html").exists())
            html = (run / "reports" / "progress.html").read_text(encoding="utf-8")
            self.assertIn("Event sequence", html)
            self.assertIn("data.snapshots", html)
            self.assertTrue((run / "reports" / "progress.md").exists())
            self.assertTrue((run / "reports" / "report-data.json").exists())

    def run_cli(self, *args: str) -> dict:
        proc = subprocess.run(
            [sys.executable, "-m", "long_horizon", *args],
            cwd=Path(__file__).resolve().parents[1],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return json.loads(proc.stdout)


if __name__ == "__main__":
    unittest.main()
