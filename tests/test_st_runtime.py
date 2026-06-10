from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from long_horizon.comments import import_comments, inbox_dir
from long_horizon.goal import create_goal, create_run
from long_horizon.install import install
from long_horizon.io import read_json, read_jsonl, read_toml, write_json
from long_horizon.logger import append_event, append_loose
from long_horizon.observer import create_observer, record_intervention
from long_horizon.paths import run_dir
from long_horizon.process import create_process, interrupt, resume
from long_horizon.report import generate_report
from long_horizon.transition import transition


class RuntimeSystemTests(unittest.TestCase):
    def make_target(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "README.md").write_text("# Target\n", encoding="utf-8")
        return root

    def create_installed_run(self) -> Path:
        root = self.make_target()
        install(root)
        self.assertFalse((root / ".agents").exists())
        install(root, apply=True)
        self.assertTrue((root / ".agents" / "rules" / "long-horizon.md").exists())
        self.assertTrue((root / ".long-horizon" / "config.toml").exists())
        contract = root / "contract.md"
        contract.write_text("# Contract\n\nGoal: ship a feature\n", encoding="utf-8")
        create_goal(root, "goal-1", contract)
        create_run(root, "goal-1", "run-1")
        return root

    def test_st_install_and_run_happy_path(self):
        root = self.create_installed_run()
        append_loose(root, "goal-1", "run-1", "messy note that cannot move workflow")
        self.assertEqual(transition(root, "goal-1", "run-1", "primary", "implement")["status"], "blocked")
        artifact = run_dir(root, "goal-1", "run-1") / "artifacts" / "plan.md"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("plan", encoding="utf-8")
        self.assertEqual(transition(root, "goal-1", "run-1", "primary", "implement")["status"], "applied")
        append_event(root, "goal-1", "run-1", "commands", "check_result", {"check_id": "tests_passed", "status": "passed"})
        self.assertEqual(transition(root, "goal-1", "run-1", "primary", "review")["status"], "applied")
        self.assertEqual(transition(root, "goal-1", "run-1", "primary", "completed")["status"], "applied")
        data = generate_report(root, "goal-1", "run-1")
        reports = run_dir(root, "goal-1", "run-1") / "reports"
        self.assertTrue((reports / "progress.html").exists())
        self.assertTrue((reports / "progress.md").exists())
        self.assertTrue((reports / "report-data.json").exists())
        self.assertGreaterEqual(len(data["events"]), 7)
        self.assertIn("#process-primary", data["anchors"])
        self.assertTrue(any(anchor.startswith("#event-") for anchor in data["anchors"]))
        self.assertEqual(data["current_state"], "completed")

    def test_st_hard_recovery_case(self):
        root = self.create_installed_run()
        interrupt(root, "goal-1", "run-1", "primary", "tmux pane exited")
        brief = (run_dir(root, "goal-1", "run-1") / "reports" / "agent-brief.md").read_text(encoding="utf-8")
        self.assertIn("Recovery Context", brief)
        resume(root, "goal-1", "run-1", "primary", "codex-thread-2")
        artifact = run_dir(root, "goal-1", "run-1") / "artifacts" / "plan.md"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("plan after resume", encoding="utf-8")
        self.assertEqual(transition(root, "goal-1", "run-1", "primary", "implement")["status"], "applied")
        events = read_jsonl(run_dir(root, "goal-1", "run-1") / "logs" / "process-events.jsonl")
        types = [event["event_type"] for event in events]
        self.assertIn("agent_session_lost", types)
        self.assertIn("process_interrupted", types)
        self.assertIn("agent_session_attached", types)
        proc = read_toml(run_dir(root, "goal-1", "run-1") / "processes" / "primary.toml")
        self.assertEqual(proc["status"], "active")
        self.assertEqual(proc["agent_session_id"], "codex-thread-2")

    def test_st_parent_child_observer_comment_report(self):
        root = self.create_installed_run()
        create_process(root, "goal-1", "run-1", "child-a", role="task", parent_process_id="primary")
        create_observer(root, "goal-1", "run-1", "watchdog", ["primary", "child-a"], ["child-a"])
        record_intervention(root, "goal-1", "run-1", "watchdog", "child-a", "check acceptance evidence")
        write_json(
            inbox_dir(root) / "local-c42.json",
            {
                "channel": "local",
                "external_comment_id": "c42",
                "external_thread_id": "thread",
                "author": "human",
                "target_refs": ["#process-child-a"],
                "body": "Why is child-a taking this path?",
            },
        )
        imported = import_comments(root, "goal-1", "run-1")
        self.assertEqual(len(imported), 1)
        data = generate_report(root, "goal-1", "run-1")
        self.assertTrue(any(edge["kind"] == "spawn" and edge["to"] == "child-a" for edge in data["communication_edges"]))
        self.assertTrue(any(edge["kind"] == "steer" and edge["to"] == "child-a" for edge in data["communication_edges"]))
        self.assertTrue(any(event["event_type"] == "human_comment" for event in data["events"]))
        board = read_toml(run_dir(root, "goal-1", "run-1") / "boards" / "task.toml")
        self.assertEqual(board["current_state"], "understand")


if __name__ == "__main__":
    unittest.main()
