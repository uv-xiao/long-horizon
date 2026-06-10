from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from long_horizon.comments import import_comments, inbox_dir
from long_horizon.config import load_config
from long_horizon.git_adapter import import_child_state, spawn_child_worktree
from long_horizon.github_adapter import GitHubAdapter, record_github_operation
from long_horizon.install import install
from long_horizon.io import read_json, read_jsonl, read_toml, write_json, write_toml
from long_horizon.mailbox import ack_message, read_mailbox, send_message
from long_horizon.observer import create_observer, record_intervention
from long_horizon.paths import boards_dir, process_amendments_path, process_flow_path, run_dir
from long_horizon.process import create_process, record_flow_amendment
from long_horizon.report import generate_report
from long_horizon.task_setup import create_task_setup, initialize_task
from long_horizon.transition import transition
from long_horizon.workflow import allowed_next


class V1CompletionUpgradeSystemTests(unittest.TestCase):
    def make_target(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "repo"
        root.mkdir()
        (root / "README.md").write_text("# Target\n", encoding="utf-8")
        return root

    def make_run(self) -> tuple[Path, str, str]:
        root = self.make_target()
        install(root, apply=True)
        task = create_task_setup(root, "Implement v1 completion test workflow", task_id="task-001")
        init = initialize_task(root, task["task_id"], "goal-v1", "run-1")
        return root, init["goal_id"], init["run_id"]

    def test_feature_settings_install_and_task_initialization(self):
        root = self.make_target()
        (root / ".long-horizon").mkdir()
        write_toml(root / ".long-horizon" / "config.toml", {"agent": {"operation_mode": "native-agent"}})
        install(root, apply=True, target_agent="codex-goal")
        config = load_config(root)
        self.assertTrue(config["features"]["runtime_state"])
        self.assertTrue(config["features"]["transition_validation"])
        self.assertTrue(config["features"]["message_mailboxes"])
        self.assertIn(config["profile"]["label"], {"native-agent-heavy", "runtime-heavy", "mixed"})
        self.assertTrue((root / ".long-horizon" / "install-plan.md").exists())

        task = create_task_setup(root, "Run a benchmark loop", task_id="task-001")
        task_dir = Path(task["task_dir"])
        self.assertTrue((task_dir / "intake.toml").exists())
        self.assertFalse((task_dir / "goal-contract.md").exists())
        initialize_task(root, "task-001", "goal-init", "run-init")
        run = run_dir(root, "goal-init", "run-init")
        self.assertTrue((run / "processes" / "primary" / "flow.toml").exists())
        self.assertTrue((run / "processes" / "primary" / "mailbox" / "inbox.jsonl").exists())

    def test_two_process_kinds_and_mailbox_fifo(self):
        root, goal_id, run_id = self.make_run()
        actor = create_process(root, goal_id, run_id, "actor", role="actor", process_kind="workspace")
        github = create_process(root, goal_id, run_id, "github", role="channel", process_kind="virtual", extra={"adapter": {"type": "github"}})
        self.assertEqual(read_toml(actor)["process_kind"], "workspace")
        self.assertEqual(read_toml(github)["workspace_path"], "")
        with self.assertRaises(ValueError):
            create_process(root, goal_id, run_id, "bad", process_kind="supervised")

        first = send_message(root, goal_id, run_id, "primary", "actor", "instruction", "first", requires_ack=True)
        second = send_message(root, goal_id, run_id, "github", "actor", "github_comment", "second")
        inbox = read_mailbox(root, goal_id, run_id, "actor")
        self.assertEqual([item["message_id"] for item in inbox], [first["message_id"], second["message_id"]])
        ack_message(root, goal_id, run_id, "actor", first["message_id"], body="accepted")
        data = generate_report(root, goal_id, run_id)
        self.assertTrue(any(message["message_id"] == first["message_id"] for message in data["mailbox_messages"]))
        self.assertTrue(any(edge.get("message_id") == second["message_id"] for edge in data["communication_edges"]))

    def test_monitor_actor_critic_and_second_generation_humanize_flow(self):
        root, goal_id, run_id = self.make_run()
        create_process(root, goal_id, run_id, "monitor", role="monitor")
        create_process(root, goal_id, run_id, "actor", role="actor", parent_process_id="monitor")
        create_process(root, goal_id, run_id, "critic", role="critic", parent_process_id="monitor")
        create_observer(root, goal_id, run_id, "observer", ["actor", "critic"], ["actor"])
        send_message(root, goal_id, run_id, "actor", "critic", "candidate_ready", "candidate A")
        send_message(root, goal_id, run_id, "critic", "actor", "review_findings", "needs stronger eval")
        record_intervention(root, goal_id, run_id, "observer", "actor", "follow critic before join")
        write_json(
            inbox_dir(root) / "human-review.json",
            {
                "channel": "local",
                "external_comment_id": "human-review",
                "external_thread_id": "review",
                "author": "human",
                "target_refs": ["#process-actor"],
                "body": "please address the observer finding",
            },
        )
        import_comments(root, goal_id, run_id)
        send_message(root, goal_id, run_id, "actor", "monitor", "evidence_ready", "fixed eval evidence")
        data = generate_report(root, goal_id, run_id)
        self.assertTrue(any(edge["from"] == "actor" and edge["to"] == "critic" for edge in data["communication_edges"]))
        self.assertTrue(any(item["target_process_id"] == "actor" for item in data["observer_interventions"]))
        self.assertTrue(any(comment["author"] == "human" for comment in data["human_comments"]))

    def test_humanize_style_fork_join_copy_on_write_and_completion_gate(self):
        root, goal_id, run_id = self.make_run()
        flow = {
            "flow": {"id": "fork-join", "initial_state": "fork", "terminal_states": ["completed"]},
            "states": [{"id": "fork", "kind": "work"}, {"id": "join", "kind": "gate"}, {"id": "completed", "kind": "terminal"}],
            "transitions": [
                {"from": "fork", "to": "join", "requires_waits": ["candidate_a_done", "candidate_b_done", "candidate_c_done"]},
                {"from": "join", "to": "completed", "requires_artifacts": ["artifacts/evals/selection.md"]},
            ],
        }
        write_toml(process_flow_path(root, goal_id, run_id, "primary"), flow)
        board = read_toml(boards_dir(root, goal_id, run_id) / "task.toml")
        board["current_state"] = "fork"
        board["allowed_next"] = allowed_next(flow, "fork")
        write_toml(boards_dir(root, goal_id, run_id) / "task.toml", board)
        for idx, wait in enumerate(["candidate_a_done", "candidate_b_done", "candidate_c_done"]):
            pid = f"candidate-{idx}"
            create_process(root, goal_id, run_id, pid, parent_process_id="primary")
            send_message(root, goal_id, run_id, pid, "primary", "candidate_result", f"result {idx}")
            from long_horizon.logger import append_event

            append_event(root, goal_id, run_id, "process-events", "process_completed", {"wait_refs": [wait]}, process_id=pid)
        self.assertEqual(transition(root, goal_id, run_id, "primary", "join")["status"], "applied")
        selection = run_dir(root, goal_id, run_id) / "artifacts" / "evals" / "selection.md"
        selection.parent.mkdir(parents=True, exist_ok=True)
        selection.write_text("selected candidate-0; rejected candidate-1 and candidate-2\n", encoding="utf-8")
        self.assertEqual(transition(root, goal_id, run_id, "primary", "completed")["status"], "applied")

    def test_real_worktree_copy_on_write_flow_and_import(self):
        root = self.make_target()
        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
        (root / "README.md").write_text("# Target\n", encoding="utf-8")
        install(root, apply=True)
        subprocess.run(["git", "add", "README.md", ".gitignore", "AGENTS.md", ".agents"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        task = create_task_setup(root, "copy-on-write test", task_id="task-cow")
        initialize_task(root, task["task_id"], "goal-cow", "run-1")
        child_path = root.parent / "repo-child"
        spawn_child_worktree(root, "goal-cow", "run-1", "primary", "child", "lh/child", child_path)
        child_flow = read_toml(process_flow_path(child_path, "goal-cow", "run-1", "child"))
        child_flow["flow"]["id"] = "child-local"
        write_toml(process_flow_path(child_path, "goal-cow", "run-1", "child"), child_flow)
        artifact = run_dir(child_path, "goal-cow", "run-1") / "artifacts" / "child.md"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("child evidence\n", encoding="utf-8")
        self.assertNotEqual(read_toml(process_flow_path(root, "goal-cow", "run-1", "child"))["flow"]["id"], "child-local")
        imported = import_child_state(root, "goal-cow", "run-1", child_path, "child", ["artifacts/child.md"])
        self.assertTrue((run_dir(root, "goal-cow", "run-1") / imported["copied_artifacts"][0]).exists())

    def test_dangerous_approval_full_github_channel_and_auth_failure_guidance(self):
        root, goal_id, run_id = self.make_run()
        blocked = record_flow_amendment(root, goal_id, run_id, "primary", "primary", "force close PR", risk_class="external_state_close")
        self.assertEqual(blocked["status"], "blocked")
        write_json(
            inbox_dir(root) / "approval.json",
            {
                "channel": "local",
                "external_comment_id": "approval",
                "external_thread_id": "approval",
                "author": "human",
                "target_refs": ["#process-primary"],
                "body": "approve dangerous external close",
            },
        )
        imported = import_comments(root, goal_id, run_id)
        recorded = record_flow_amendment(root, goal_id, run_id, "primary", "primary", "force close PR", risk_class="external_state_close", approval_refs=[imported[0]["event_id"]])
        self.assertEqual(recorded["status"], "recorded")
        for op, target in [("create_issue", "issue"), ("comment_issue", "issue"), ("close_issue", "issue"), ("create_pr", "pr"), ("comment_pr", "pr"), ("close_pr", "pr")]:
            result = record_github_operation(root, goal_id, run_id, op, target, title="title", body="body", number=1, head="feature", base="main")
            self.assertIn("agent_skill_brief", result["operation"])
        with self.assertRaisesRegex(RuntimeError, "No repo-local gh auth|GitHub CLI is not installed"):
            GitHubAdapter(root, require_auth=True).verify_auth()
        data = generate_report(root, goal_id, run_id)
        self.assertTrue(any(msg["message_type"].startswith("github_") for msg in data["mailbox_messages"]))
        self.assertTrue(read_jsonl(process_amendments_path(root, goal_id, run_id, "primary")))

    def test_prompt_skill_deposition_merge_repair_and_report_completeness(self):
        root, goal_id, run_id = self.make_run()
        for skill in [
            "rate-prompt-template",
            "improve-skill-body",
            "plan-long-horizon-install",
            "promote-skill",
            "promote-rule",
            "promote-memory",
            "promote-adapter",
            "merge-conflict-repair",
        ]:
            self.assertTrue((root / ".agents" / "skills" / skill / "SKILL.md").exists())
        for prompt in ["promote-skill.md", "promote-rule.md", "promote-memory.md", "promote-adapter.md", "merge-conflict-repair.md"]:
            self.assertTrue((root / ".agents" / "templates" / "long-horizon" / prompt).exists())

        dep = run_dir(root, goal_id, run_id) / "artifacts" / "deposition" / "promote-skill.md"
        dep.parent.mkdir(parents=True, exist_ok=True)
        dep.write_text("problem/evidence/scope/counterexamples/validation/rollback\n", encoding="utf-8")
        merge_patch = run_dir(root, goal_id, run_id) / "artifacts" / "merge-repair" / "proposed.patch"
        merge_patch.parent.mkdir(parents=True, exist_ok=True)
        merge_patch.write_text("proposed patch before apply\n", encoding="utf-8")
        from long_horizon.logger import append_event

        append_event(root, goal_id, run_id, "artifacts", "deposition_recorded", {"path": "artifacts/deposition/promote-skill.md"}, process_id="primary")
        append_event(root, goal_id, run_id, "artifacts", "merge_repair_proposed", {"path": "artifacts/merge-repair/proposed.patch"}, process_id="primary")
        data = generate_report(root, goal_id, run_id)
        reports = run_dir(root, goal_id, run_id) / "reports"
        self.assertTrue((reports / "progress.html").exists())
        self.assertTrue((reports / "progress.md").exists())
        self.assertTrue((reports / "report-data.json").exists())
        self.assertFalse((reports / "slides.html").exists())
        self.assertFalse((reports / "slides-data.json").exists())
        self.assertIn("feature_settings", data)
        self.assertIn("mailboxes", data)
        self.assertTrue(any(event["event_type"] == "deposition_recorded" for event in data["events"]))
        self.assertTrue(any(event["event_type"] == "merge_repair_proposed" for event in data["events"]))


if __name__ == "__main__":
    unittest.main()
