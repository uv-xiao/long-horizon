from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from long_horizon.comments import import_comments, inbox_dir
from long_horizon.config import set_config_value, validate_config
from long_horizon.goal import create_goal, create_run
from long_horizon.install import install
from long_horizon.io import read_json, read_jsonl, read_toml, write_json, write_toml
from long_horizon.logger import append_event, append_loose
from long_horizon.mailbox import ack_message, read_mailbox, send_message
from long_horizon.observer import create_observer, record_intervention
from long_horizon.paths import boards_dir, process_amendments_path, process_flow_path, run_dir
from long_horizon.process import create_process, interrupt, record_flow_amendment, resume
from long_horizon.transition import transition


class RuntimeUnitTests(unittest.TestCase):
    def make_run(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        install(root, apply=True)
        contract = root / "contract.md"
        contract.write_text("# Contract\n\nGoal: test\n", encoding="utf-8")
        create_goal(root, "goal-1", contract)
        create_run(root, "goal-1", "run-1")
        return root

    def test_config_validation_rejects_invalid_policy(self):
        root = self.make_run()
        with self.assertRaises(ValueError):
            set_config_value(root, "process.workspace_mode", "telepathy")
        self.assertEqual(validate_config(root), [])

    def test_logger_typed_sequence_and_malformed_payload(self):
        root = self.make_run()
        first = append_event(root, "goal-1", "run-1", "commands", "command_ran", {"cmd": "true"})
        second = append_event(root, "goal-1", "run-1", "commands", "command_ran", {"cmd": "false"})
        self.assertEqual(first["seq"], 1)
        self.assertEqual(second["seq"], 2)
        self.assertEqual(second["prev_hash"], first["event_hash"])
        with self.assertRaises(ValueError):
            append_event(root, "goal-1", "run-1", "commands", "bad", ["not-object"])  # type: ignore[arg-type]

    def test_loose_logs_do_not_drive_transitions(self):
        root = self.make_run()
        append_loose(root, "goal-1", "run-1", "plan exists", tags=["artifact"])
        result = transition(root, "goal-1", "run-1", "primary", "implement")
        self.assertEqual(result["status"], "blocked")
        self.assertIn("missing artifact artifacts/plan.md", result["reasons"])

    def test_transition_blocks_and_applies_artifact_check_and_human_gates(self):
        root = self.make_run()
        result = transition(root, "goal-1", "run-1", "primary", "implement")
        self.assertEqual(result["status"], "blocked")
        artifact = run_dir(root, "goal-1", "run-1") / "artifacts" / "plan.md"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("plan", encoding="utf-8")
        self.assertEqual(transition(root, "goal-1", "run-1", "primary", "implement")["status"], "applied")
        self.assertEqual(transition(root, "goal-1", "run-1", "primary", "review")["status"], "blocked")
        append_event(root, "goal-1", "run-1", "commands", "check_result", {"check_id": "tests_passed", "status": "passed"})
        self.assertEqual(transition(root, "goal-1", "run-1", "primary", "review")["status"], "applied")

        flow_path = process_flow_path(root, "goal-1", "run-1", "primary")
        flow = read_toml(flow_path)
        for trans in flow["transitions"]:
            if trans["from"] == "review" and trans["to"] == "completed":
                trans["requires_human"] = True
                trans["human_gate"] = "completed"
        write_toml(flow_path, flow)
        self.assertEqual(transition(root, "goal-1", "run-1", "primary", "completed")["status"], "blocked")
        append_event(root, "goal-1", "run-1", "human", "human_comment", {"classification": "approval", "target_refs": ["completed"]})
        self.assertEqual(transition(root, "goal-1", "run-1", "primary", "completed")["status"], "applied")

    def test_process_kind_validation_rejects_non_v1_kinds(self):
        root = self.make_run()
        with self.assertRaises(ValueError):
            create_process(root, "goal-1", "run-1", "external-service", process_kind="external")
        path = create_process(root, "goal-1", "run-1", "github", role="channel", process_kind="virtual")
        data = read_toml(path)
        self.assertEqual(data["process_kind"], "virtual")
        self.assertEqual(data["workspace_path"], "")

    def test_mailbox_send_deliver_ack_preserves_fifo(self):
        root = self.make_run()
        create_process(root, "goal-1", "run-1", "critic", role="critic")
        first = send_message(root, "goal-1", "run-1", "primary", "critic", "question", "first", requires_ack=True)
        second = send_message(root, "goal-1", "run-1", "primary", "critic", "question", "second")
        inbox = read_mailbox(root, "goal-1", "run-1", "critic", "inbox")
        self.assertEqual([item["message_id"] for item in inbox], [first["message_id"], second["message_id"]])
        ack = ack_message(root, "goal-1", "run-1", "critic", first["message_id"], body="seen")
        self.assertEqual(ack["status"], "acknowledged")
        outbox = read_mailbox(root, "goal-1", "run-1", "primary", "outbox")
        self.assertEqual(len(outbox), 2)

    def test_mailbox_message_only_satisfies_declared_message_gate(self):
        root = self.make_run()
        flow_path = process_flow_path(root, "goal-1", "run-1", "primary")
        flow = read_toml(flow_path)
        for trans in flow["transitions"]:
            if trans["from"] == "understand" and trans["to"] == "implement":
                trans.pop("requires_artifacts", None)
                trans["requires_messages"] = ["human_comment"]
        write_toml(flow_path, flow)
        blocked = transition(root, "goal-1", "run-1", "primary", "implement")
        self.assertEqual(blocked["status"], "blocked")
        self.assertIn("missing message human_comment", blocked["reasons"])
        create_process(root, "goal-1", "run-1", "human", role="human", process_kind="virtual")
        send_message(root, "goal-1", "run-1", "human", "primary", "human_comment", "go")
        self.assertEqual(transition(root, "goal-1", "run-1", "primary", "implement")["status"], "applied")

    def test_dangerous_workflow_amendment_requires_approval(self):
        root = self.make_run()
        blocked = record_flow_amendment(root, "goal-1", "run-1", "primary", "primary", "weaken AC", risk_class="acceptance_weakening")
        self.assertEqual(blocked["status"], "blocked")
        recorded = record_flow_amendment(
            root,
            "goal-1",
            "run-1",
            "primary",
            "primary",
            "weaken AC",
            risk_class="acceptance_weakening",
            approval_refs=["evt_human_approval"],
        )
        self.assertEqual(recorded["status"], "recorded")
        amendments = read_jsonl(process_amendments_path(root, "goal-1", "run-1", "primary"))
        self.assertEqual(len(amendments), 1)

    def test_process_interruption_resume_regenerates_brief(self):
        root = self.make_run()
        interrupt(root, "goal-1", "run-1", "primary", "session quit")
        brief = run_dir(root, "goal-1", "run-1") / "reports" / "agent-brief.md"
        self.assertIn("Recovery Context", brief.read_text(encoding="utf-8"))
        resume(root, "goal-1", "run-1", "primary", "new-session")
        proc = read_toml(run_dir(root, "goal-1", "run-1") / "processes" / "primary.toml")
        self.assertEqual(proc["status"], "active")
        self.assertEqual(proc["agent_session_id"], "new-session")

    def test_observer_intervention_is_append_only_and_does_not_mutate_task_board(self):
        root = self.make_run()
        before = read_toml(boards_dir(root, "goal-1", "run-1") / "task.toml")
        create_observer(root, "goal-1", "run-1", "watchdog", ["primary"], ["primary"])
        record_intervention(root, "goal-1", "run-1", "watchdog", "primary", "stay on plan")
        after = read_toml(boards_dir(root, "goal-1", "run-1") / "task.toml")
        self.assertEqual(before, after)
        events = read_jsonl(run_dir(root, "goal-1", "run-1") / "logs" / "observer-events.jsonl")
        self.assertEqual([e["event_type"] for e in events], ["intervention_requested", "intervention_delivered"])

    def test_comment_import_deduplicates_push_envelopes(self):
        root = self.make_run()
        envelope = {
            "channel": "local",
            "external_comment_id": "c1",
            "external_thread_id": "t1",
            "author": "human",
            "target_refs": ["event:evt_000001"],
            "body": "Looks good?",
        }
        path = inbox_dir(root) / "local-c1.json"
        write_json(path, envelope)
        first = import_comments(root, "goal-1", "run-1")
        write_json(path, envelope)
        second = import_comments(root, "goal-1", "run-1")
        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 0)
        events = read_jsonl(run_dir(root, "goal-1", "run-1") / "logs" / "human.jsonl")
        self.assertEqual(len(events), 1)


if __name__ == "__main__":
    unittest.main()
