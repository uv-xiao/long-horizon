from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from long_horizon.comments import import_comments, inbox_dir
from long_horizon.goal import create_goal, create_run
from long_horizon.install import install
from long_horizon.io import read_toml, write_json, write_toml
from long_horizon.logger import append_event
from long_horizon.observer import create_observer, record_intervention
from long_horizon.paths import boards_dir, run_dir
from long_horizon.process import create_process
from long_horizon.report import generate_report
from long_horizon.transition import transition
from long_horizon.workflow import allowed_next


class HumanizeStyleSystemTests(unittest.TestCase):
    def make_run(self, flow: dict, contract_text: str) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        install(root, apply=True)
        contract = root / "contract.md"
        contract.write_text(contract_text, encoding="utf-8")
        create_goal(root, "goal-humanize", contract)
        create_run(root, "goal-humanize", "run-1")
        write_toml(run_dir(root, "goal-humanize", "run-1") / "flow.snapshot.toml", flow)
        initial = flow["flow"]["initial_state"]
        board = read_toml(boards_dir(root, "goal-humanize", "run-1") / "task.toml")
        board["current_state"] = initial
        board["allowed_next"] = allowed_next(flow, initial)
        write_toml(boards_dir(root, "goal-humanize", "run-1") / "task.toml", board)
        return root

    def test_humanize_v1_two_loops_with_inner_fork_join_and_real_human_observer_report(self):
        flow = {
            "flow": {"id": "humanize-v1-nested", "initial_state": "plan_acceptance", "terminal_states": ["completed"]},
            "states": [
                {"id": "plan_acceptance", "kind": "human_gate"},
                {"id": "build_round", "kind": "builder_loop"},
                {"id": "review_round", "kind": "reviewer_loop"},
                {"id": "fork_join_exploration", "kind": "parallel_inner_loop"},
                {"id": "final_audit", "kind": "audit"},
                {"id": "completed", "kind": "terminal"},
            ],
            "transitions": [
                {"from": "plan_acceptance", "to": "build_round", "requires_human": True, "human_gate": "plan_accepted"},
                {"from": "build_round", "to": "review_round", "requires_artifacts": ["artifacts/round-001/builder-summary.md"]},
                {"from": "review_round", "to": "fork_join_exploration", "requires_checks": ["round_001_progress_review_passed"]},
                {"from": "fork_join_exploration", "to": "final_audit", "requires_waits": ["candidate_fast_done", "candidate_safe_done"]},
                {"from": "final_audit", "to": "completed", "requires_human": True, "human_gate": "final_acceptance"},
            ],
        }
        root = self.make_run(
            flow,
            "# Humanize v1 mimic\n\nPlan-first RLCR loop with a nested fork-join exploration inside the builder loop.\n",
        )
        run = run_dir(root, "goal-humanize", "run-1")
        self.assertEqual(transition(root, "goal-humanize", "run-1", "primary", "build_round")["status"], "blocked")

        write_json(
            inbox_dir(root) / "local-plan-approval.json",
            {
                "channel": "local",
                "external_comment_id": "plan-approval",
                "external_thread_id": "thread-plan",
                "author": "architect",
                "target_refs": ["plan_accepted"],
                "body": "approve plan acceptance criteria",
            },
        )
        import_comments(root, "goal-humanize", "run-1")
        self.assertEqual(transition(root, "goal-humanize", "run-1", "primary", "build_round")["status"], "applied")

        _fake_builder_round(root, "goal-humanize", "run-1", "primary", "round-001")
        self.assertEqual(transition(root, "goal-humanize", "run-1", "primary", "review_round")["status"], "applied")
        append_event(
            root,
            "goal-humanize",
            "run-1",
            "reviews",
            "review_verdict",
            {"round": "round-001", "verdict": "continue", "blocking_findings": 0, "target_process_id": "primary"},
        )
        append_event(
            root,
            "goal-humanize",
            "run-1",
            "commands",
            "check_result",
            {"check_id": "round_001_progress_review_passed", "status": "passed"},
        )
        self.assertEqual(transition(root, "goal-humanize", "run-1", "primary", "fork_join_exploration")["status"], "applied")

        create_process(root, "goal-humanize", "run-1", "candidate-fast", role="task", parent_process_id="primary")
        create_process(root, "goal-humanize", "run-1", "candidate-safe", role="task", parent_process_id="primary")
        create_observer(root, "goal-humanize", "run-1", "watchdog", ["primary", "candidate-fast", "candidate-safe"], ["candidate-fast"])
        _fake_candidate(root, "goal-humanize", "run-1", "candidate-fast", "candidate_fast_done", "fast path")
        record_intervention(root, "goal-humanize", "run-1", "watchdog", "candidate-fast", "prove AC-2 before merge")
        partial_join = transition(root, "goal-humanize", "run-1", "primary", "final_audit")
        self.assertEqual(partial_join["status"], "blocked")
        self.assertIn("wait not satisfied candidate_safe_done", partial_join["reasons"])
        _fake_candidate(root, "goal-humanize", "run-1", "candidate-safe", "candidate_safe_done", "safe path")
        self.assertEqual(transition(root, "goal-humanize", "run-1", "primary", "final_audit")["status"], "applied")
        append_event(
            root,
            "goal-humanize",
            "run-1",
            "artifacts",
            "artifact_imported",
            {"artifact_id": "selected-candidate", "from_process_id": "candidate-fast", "target_process_id": "primary", "path": "artifacts/imports/selected-candidate.md"},
        )
        write_json(
            inbox_dir(root) / "local-final-approval.json",
            {
                "channel": "local",
                "external_comment_id": "final-approval",
                "external_thread_id": "thread-final",
                "author": "architect",
                "target_refs": ["final_acceptance", "#process-candidate-fast"],
                "body": "approve final acceptance",
            },
        )
        import_comments(root, "goal-humanize", "run-1")
        self.assertEqual(transition(root, "goal-humanize", "run-1", "primary", "completed")["status"], "applied")

        data = generate_report(root, "goal-humanize", "run-1")
        html = (run / "reports" / "progress.html").read_text(encoding="utf-8")
        self.assertEqual(data["playback"]["axis"], "event_sequence")
        self.assertEqual(len(data["snapshots"]), len(data["events"]))
        self.assertGreaterEqual(len(data["events"]), 20)
        self.assertIn("observer", data["event_lanes"])
        self.assertIn("human", data["event_lanes"])
        self.assertTrue(any(edge["kind"] == "spawn" and edge["to"] == "candidate-fast" for edge in data["communication_edges"]))
        self.assertTrue(any(edge["kind"] == "artifact_import" for edge in data["communication_edges"]))
        self.assertTrue(any(edge["kind"] == "steer" and edge["to"] == "candidate-fast" for edge in data["communication_edges"]))
        self.assertTrue(any(comment["author"] == "architect" for comment in data["human_comments"]))
        self.assertTrue(any(item["target_process_id"] == "candidate-fast" for item in data["observer_interventions"]))
        self.assertTrue(any(lane["lane_id"] == "process:candidate-fast" for lane in data["timeline"]["lanes"]))
        self.assertTrue(any(message["kind"] == "artifact_import" for message in data["timeline"]["messages"]))
        self.assertTrue(any(message["kind"] == "steer" and message["to_lane_id"] == "process:candidate-fast" for message in data["timeline"]["messages"]))
        self.assertTrue(any(marker["event_type"] == "human_comment" for marker in data["timeline"]["event_markers"]))
        self.assertIn("perfetto-timeline", html)
        self.assertIn("timeline-message-link", html)
        self.assertIn("state-transition-diagram", html)

    def test_humanize_v2_plan_lifecycle_rlcr_alignment_and_methodology_report(self):
        flow = {
            "flow": {"id": "humanize-v2-plan-constitution", "initial_state": "plan_expansion", "terminal_states": ["completed"]},
            "states": [
                {"id": "plan_expansion", "kind": "architect"},
                {"id": "adversarial_plan_critique", "kind": "critic"},
                {"id": "plan_acceptance_gate", "kind": "human_gate"},
                {"id": "rlcr_round", "kind": "builder_reviewer_loop"},
                {"id": "full_alignment_check", "kind": "observer_audit"},
                {"id": "plan_amendment_review", "kind": "human_gate"},
                {"id": "methodology_report", "kind": "deposition"},
                {"id": "completed", "kind": "terminal"},
            ],
            "transitions": [
                {"from": "plan_expansion", "to": "adversarial_plan_critique", "requires_artifacts": ["artifacts/plan/expanded-plan.md"]},
                {"from": "adversarial_plan_critique", "to": "plan_acceptance_gate", "requires_checks": ["plan_survives_adversarial_reading"]},
                {"from": "plan_acceptance_gate", "to": "rlcr_round", "requires_human": True, "human_gate": "plan_accepted"},
                {"from": "rlcr_round", "to": "full_alignment_check", "requires_artifacts": ["artifacts/round-005/delta-card.md"]},
                {"from": "full_alignment_check", "to": "plan_amendment_review", "requires_checks": ["alignment_check_needs_amendment"]},
                {"from": "plan_amendment_review", "to": "methodology_report", "requires_human": True, "human_gate": "amendment_approved"},
                {"from": "methodology_report", "to": "completed", "requires_artifacts": ["artifacts/methodology/process-report.md"]},
            ],
        }
        root = self.make_run(flow, "# Humanize v2 mimic\n\nPlan constitution, RLCR, full alignment check, amendment, methodology deposition.\n")
        run = run_dir(root, "goal-humanize", "run-1")
        _write_artifact(run, "artifacts/plan/expanded-plan.md", "goal, acceptance, constraints, milestones")
        self.assertEqual(transition(root, "goal-humanize", "run-1", "primary", "adversarial_plan_critique")["status"], "applied")
        append_event(
            root,
            "goal-humanize",
            "run-1",
            "reviews",
            "plan_critique",
            {"questions": ["is done cheaper to check?", "which constraints are tempting to spend?"], "target_process_id": "primary"},
        )
        append_event(
            root,
            "goal-humanize",
            "run-1",
            "commands",
            "check_result",
            {"check_id": "plan_survives_adversarial_reading", "status": "passed"},
        )
        self.assertEqual(transition(root, "goal-humanize", "run-1", "primary", "plan_acceptance_gate")["status"], "applied")
        write_json(
            inbox_dir(root) / "local-v2-plan.json",
            {
                "channel": "local",
                "external_comment_id": "v2-plan",
                "external_thread_id": "thread-v2",
                "author": "architect",
                "target_refs": ["plan_accepted", "#state-at-0"],
                "body": "approve v2 plan constitution",
            },
        )
        import_comments(root, "goal-humanize", "run-1")
        self.assertEqual(transition(root, "goal-humanize", "run-1", "primary", "rlcr_round")["status"], "applied")
        _write_artifact(run, "artifacts/round-005/delta-card.md", "changed files match round summary; frozen files untouched")
        append_event(root, "goal-humanize", "run-1", "commands", "delta_card", {"round": 5, "status": "matched", "target_process_id": "primary"})
        self.assertEqual(transition(root, "goal-humanize", "run-1", "primary", "full_alignment_check")["status"], "applied")
        create_observer(root, "goal-humanize", "run-1", "alignment-watchdog", ["primary"], ["primary"])
        record_intervention(root, "goal-humanize", "run-1", "alignment-watchdog", "primary", "full alignment check found missing batch=1 acceptance")
        append_event(
            root,
            "goal-humanize",
            "run-1",
            "commands",
            "check_result",
            {"check_id": "alignment_check_needs_amendment", "status": "passed"},
        )
        self.assertEqual(transition(root, "goal-humanize", "run-1", "primary", "plan_amendment_review")["status"], "applied")
        write_json(
            inbox_dir(root) / "local-v2-amendment.json",
            {
                "channel": "local",
                "external_comment_id": "v2-amendment",
                "external_thread_id": "thread-v2",
                "author": "architect",
                "target_refs": ["amendment_approved"],
                "body": "approve amendment: add batch=1 acceptance case",
            },
        )
        import_comments(root, "goal-humanize", "run-1")
        self.assertEqual(transition(root, "goal-humanize", "run-1", "primary", "methodology_report")["status"], "applied")
        _write_artifact(run, "artifacts/methodology/process-report.md", "methodology issue: acceptance set lacked batch=1")
        append_event(
            root,
            "goal-humanize",
            "run-1",
            "artifacts",
            "methodology_report_created",
            {"artifact_id": "methodology-report", "path": "artifacts/methodology/process-report.md", "target_process_id": "primary"},
        )
        self.assertEqual(transition(root, "goal-humanize", "run-1", "primary", "completed")["status"], "applied")
        data = generate_report(root, "goal-humanize", "run-1")
        self.assertEqual(data["current_state"], "completed")
        self.assertTrue(any(event["event_type"] == "plan_critique" for event in data["events"]))
        self.assertTrue(any(event["event_type"] == "delta_card" for event in data["events"]))
        self.assertTrue(any(event["event_type"] == "methodology_report_created" for event in data["events"]))
        self.assertTrue(any(item["message"].startswith("full alignment check") for item in data["observer_interventions"]))
        self.assertGreaterEqual(len(data["snapshots"]), 15)
        self.assertIn("#state-at-0", data["anchors"])
        self.assertTrue(any(segment["state"] == "methodology_report" for lane in data["timeline"]["lanes"] for segment in lane.get("state_segments", [])))
        self.assertTrue(any(marker["event_type"] == "methodology_report_created" for marker in data["timeline"]["event_markers"]))


def _fake_builder_round(root: Path, goal_id: str, run_id: str, process_id: str, round_id: str) -> None:
    run = run_dir(root, goal_id, run_id)
    _write_artifact(run, f"artifacts/{round_id}/builder-summary.md", "implemented task slice, tests pending")
    append_event(root, goal_id, run_id, "commands", "builder_round", {"round": round_id, "status": "summarized"}, process_id=process_id)


def _fake_candidate(root: Path, goal_id: str, run_id: str, process_id: str, wait_ref: str, result: str) -> None:
    run = run_dir(root, goal_id, run_id)
    _write_artifact(run, f"artifacts/candidates/{process_id}.md", result)
    append_event(root, goal_id, run_id, "artifacts", "artifact_created", {"artifact_id": process_id, "path": f"artifacts/candidates/{process_id}.md"}, process_id=process_id)
    append_event(root, goal_id, run_id, "process-events", "process_completed", {"wait_refs": [wait_ref], "result": result}, process_id=process_id)


def _write_artifact(run: Path, rel: str, body: str) -> None:
    path = run / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
