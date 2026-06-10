from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import tempfile
import unittest
from pathlib import Path

from long_horizon.evaluation import run_evaluation
from long_horizon.install import install
from long_horizon.io import read_json, read_jsonl, write_toml
from long_horizon.ledger_recovery import reconcile_ledger
from long_horizon.logger import append_event, ledger_path
from long_horizon.merge_repair import propose_merge_repair
from long_horizon.notification import send_notification
from long_horizon.paths import reports_dir, run_dir
from long_horizon.promotion import promote_artifact
from long_horizon.report import generate_report
from long_horizon.report_gui import write_report_gui_manifest
from long_horizon.retention import run_retention_sidecar
from long_horizon.supervisor import reap_supervised_process, start_supervised_process, supervised_status
from long_horizon.task_setup import create_task_setup, initialize_task


class V1StatusCompletionSystemTests(unittest.TestCase):
    def make_run(self) -> tuple[Path, str, str]:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "repo"
        root.mkdir()
        (root / "README.md").write_text("# Target\n", encoding="utf-8")
        install(root, apply=True, target_agent="codex-goal")
        task = create_task_setup(root, "Complete all v1 status features", task_id="task-status")
        init = initialize_task(root, task["task_id"], "goal-status", "run-1")
        return root, init["goal_id"], init["run_id"]

    def test_remaining_v1_features_are_runtime_backed_and_reported(self):
        root, goal_id, run_id = self.make_run()

        supervised_out = root / "supervised.txt"
        start_supervised_process(
            root,
            goal_id,
            run_id,
            "worker",
            [sys.executable, "-c", f"from pathlib import Path; Path({str(supervised_out)!r}).write_text('done')"],
            cwd=root,
            restart_policy="never",
        )
        for _ in range(30):
            reaped = reap_supervised_process(root, goal_id, run_id, "worker")
            if reaped["handle"]["status"] == "exited":
                break
            time.sleep(0.05)
        self.assertEqual(read_json(run_dir(root, goal_id, run_id) / "artifacts" / "supervisor" / "worker" / "handle.json")["status"], "exited")
        self.assertEqual(supervised_out.read_text(encoding="utf-8"), "done")

        send_notification(root, goal_id, run_id, "local", "Review Ready", "open the report")
        send_notification(root, goal_id, run_id, "github", "PR Review", "please review", github_target="pr", number=7)

        evidence = run_dir(root, goal_id, run_id) / "artifacts" / "evidence.txt"
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text("needle\n", encoding="utf-8")
        self.assertEqual(run_evaluation(root, goal_id, run_id, "file-check", "file_contains", file_path=str(evidence.relative_to(root)), contains="needle")["evaluation"]["status"], "passed")
        self.assertEqual(run_evaluation(root, goal_id, run_id, "metric-check", "metric_threshold", metric_name="score", metric_value=0.91, threshold=0.9)["evaluation"]["status"], "passed")
        self.assertEqual(run_evaluation(root, goal_id, run_id, "command-check", "command", command=f"{sys.executable} -c \"print('ok')\"")["evaluation"]["status"], "passed")

        promo = run_dir(root, goal_id, run_id) / "artifacts" / "deposition" / "skill.md"
        promo.parent.mkdir(parents=True, exist_ok=True)
        promo.write_text("# Skill\n\nproblem\nevidence\nscope\nvalidation\nrollback\n", encoding="utf-8")
        for kind in ["skill", "rule", "memory", "adapter"]:
            result = promote_artifact(root, goal_id, run_id, kind, f"status-{kind}", "artifacts/deposition/skill.md")
            self.assertEqual(result["status"], "applied")
            self.assertTrue(Path(result["destination"]).exists())

        large = run_dir(root, goal_id, run_id) / "artifacts" / "raw" / "large.txt"
        large.parent.mkdir(parents=True, exist_ok=True)
        large.write_text("x" * 128, encoding="utf-8")
        retention = run_retention_sidecar(root, goal_id, run_id, min_bytes=100)
        self.assertTrue(retention["records"])
        self.assertTrue(Path(retention["manifest"]).exists())

        first = append_event(root, goal_id, run_id, "commands", "command_ran", {"cmd": "true"})
        second = append_event(root, goal_id, run_id, "commands", "command_ran", {"cmd": "false"})
        path = ledger_path(root, goal_id, run_id, "commands")
        events = read_jsonl(path)
        events[-1]["prev_hash"] = "corrupted"
        path.write_text("".join(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n" for event in events), encoding="utf-8")
        recovery = reconcile_ledger(root, goal_id, run_id, "commands")
        self.assertTrue(recovery["report"]["issues"])
        self.assertTrue((run_dir(root, goal_id, run_id) / recovery["report"]["reconciled_copy"]).exists())
        self.assertEqual(second["seq"], first["seq"] + 1)

        conflict = root / "conflicted.txt"
        conflict.write_text("a\n<<<<<<< ours\nleft\n=======\nright\n>>>>>>> theirs\nz\n", encoding="utf-8")
        blocked = propose_merge_repair(root, goal_id, run_id, "conflicted.txt", apply=True)
        self.assertEqual(blocked["status"], "blocked")
        applied = propose_merge_repair(root, goal_id, run_id, "conflicted.txt", approval_refs=["evt_human_approval"], apply=True)
        self.assertEqual(applied["status"], "applied")
        self.assertNotIn("<<<<<<<", conflict.read_text(encoding="utf-8"))

        manifest = write_report_gui_manifest(root, goal_id, run_id, adapter="static-html")
        self.assertEqual(manifest["manifest"]["boundary"], "report-data-json")
        data = generate_report(root, goal_id, run_id)
        mechanisms = data["mechanism_evidence"]
        for name in [
            "supervisor",
            "notifications",
            "evaluations",
            "promotion",
            "retention",
            "ledger_recovery",
            "merge_repair",
            "report_gui",
        ]:
            self.assertIn(name, mechanisms)
            self.assertTrue(mechanisms[name]["events"] or mechanisms[name]["artifacts"], name)
        event_types = {event["event_type"] for event in data["events"]}
        self.assertIn("supervisor_process_started", event_types)
        self.assertIn("notification_sent", event_types)
        self.assertIn("evaluation_recorded", event_types)
        self.assertIn("promotion_applied", event_types)
        self.assertIn("artifact_retained", event_types)
        self.assertIn("ledger_reconciled", event_types)
        self.assertIn("merge_repair_applied", event_types)
        self.assertIn("report_gui_manifest_written", event_types)
        self.assertTrue((reports_dir(root, goal_id, run_id) / "report-gui-manifest.json").exists())
        self.assertIn("## Mechanism Evidence", (reports_dir(root, goal_id, run_id) / "progress.md").read_text(encoding="utf-8"))

    def test_installable_skills_and_config_surface_cover_status_features(self):
        root, goal_id, run_id = self.make_run()
        expected_skills = [
            "analyze-target-agent",
            "configure-long-horizon",
            "install-long-horizon",
            "plan-long-horizon-install",
            "promote-skill",
            "promote-rule",
            "promote-memory",
            "promote-adapter",
            "merge-conflict-repair",
        ]
        for skill in expected_skills:
            self.assertTrue((root / ".agents" / "skills" / skill / "SKILL.md").exists(), skill)
        config = read_json(run_dir(root, goal_id, run_id) / "reports" / "report-data.json")
        self.assertIn("feature_settings", config)

    def test_installable_mechanism_skills_have_completion_contracts(self):
        root, _goal_id, _run_id = self.make_run()
        for skill in [
            "operate-long-horizon-process",
            "promote-skill",
            "promote-rule",
            "promote-memory",
            "promote-adapter",
            "merge-conflict-repair",
            "configure-long-horizon",
        ]:
            body = (root / ".agents" / "skills" / skill / "SKILL.md").read_text(encoding="utf-8").lower()
            for required in [
                "purpose",
                "scope",
                "required reads",
                "allowed writes",
                "workflow",
                "produced artifacts",
                "commands",
                "failure",
                "completion evidence",
                "example",
            ]:
                self.assertIn(required, body, f"{skill} missing {required}")

    def test_github_execution_failure_is_durable_channel_evidence(self):
        from long_horizon.github_adapter import record_github_operation

        root, goal_id, run_id = self.make_run()
        result = record_github_operation(
            root,
            goal_id,
            run_id,
            "comment_pr",
            "pr",
            title="Review",
            body="please inspect",
            number=123,
            execute=True,
        )
        operation = result["operation"]
        self.assertEqual(operation["status"], "failed")
        self.assertIn("setup_guidance", operation)
        self.assertIn("repo-local", operation["setup_guidance"])
        data = generate_report(root, goal_id, run_id)
        self.assertTrue(data["mechanism_evidence"]["github_operations"]["events"])
        self.assertTrue(any(event["event_type"] == "github_operation_failed" for event in data["events"]))

    def test_source_backed_merge_repair_records_context_and_eval_evidence(self):
        root, goal_id, run_id = self.make_run()
        conflict = root / "conflicted.txt"
        conflict.write_text("a\n<<<<<<< ours\nleft\n=======\nright\n>>>>>>> theirs\nz\n", encoding="utf-8")
        result = propose_merge_repair(
            root,
            goal_id,
            run_id,
            "conflicted.txt",
            base_ref="base-sha",
            parent_ref="parent-sha",
            child_ref="child-sha",
            merge_failure_event_id="evt_merge_failed",
            eval_refs=["eval_unit_passed"],
            source_note_refs=["artifacts/merge-repair/source-notes.md"],
            apply=False,
        )
        record = result["record"]
        self.assertEqual(record["status"], "proposed")
        self.assertEqual(record["base_ref"], "base-sha")
        self.assertEqual(record["parent_ref"], "parent-sha")
        self.assertEqual(record["child_ref"], "child-sha")
        self.assertEqual(record["merge_failure_event_id"], "evt_merge_failed")
        self.assertEqual(record["eval_refs"], ["eval_unit_passed"])
        self.assertEqual(record["source_note_refs"], ["artifacts/merge-repair/source-notes.md"])
        self.assertTrue(record["conflict_markers"]["ours"])
        self.assertTrue(record["conflict_markers"]["theirs"])
        self.assertTrue((run_dir(root, goal_id, run_id) / record["proposed_patch"]).exists())
        data = generate_report(root, goal_id, run_id)
        self.assertTrue(data["mechanism_evidence"]["merge_repair"]["artifacts"])

    def test_feature_completion_audit_and_status_align_with_runtime_evidence(self):
        repo = Path(__file__).resolve().parents[1]
        status = (repo / "STATUS.md").read_text(encoding="utf-8")
        audit = (repo / "docs" / "v1-feature-completion-audit.md").read_text(encoding="utf-8")
        coverage = (repo / "docs" / "v1-system-test-coverage.md").read_text(encoding="utf-8")
        for required in [
            "mechanism_evidence",
            "github_operation_failed",
            "test_source_backed_merge_repair_records_context_and_eval_evidence",
            "test_installable_mechanism_skills_have_completion_contracts",
            "test_github_execution_failure_is_durable_channel_evidence",
        ]:
            self.assertIn(required, status + audit + coverage)
        for mechanism in [
            "supervisor",
            "notifications",
            "github_operations",
            "evaluations",
            "promotion",
            "retention",
            "ledger_recovery",
            "merge_repair",
            "report_gui",
        ]:
            self.assertIn(mechanism, audit)
        self.assertNotIn("partial", status.lower())
        self.assertNotIn("planned", status.lower())
        for doc in (repo / "docs").glob("*.md"):
            text = doc.read_text(encoding="utf-8")
            self.assertNotIn("docs/v1-upgrade-negotiation", text)

    def test_cli_status_completion_commands_are_agent_usable(self):
        root, goal_id, run_id = self.make_run()
        self._cli(root, "notify", "--root", str(root), "--goal-id", goal_id, "--run-id", run_id, "--channel", "local", "--subject", "CLI", "--body", "hello")
        self._cli(
            root,
            "evaluation",
            "run",
            "--root",
            str(root),
            "--goal-id",
            goal_id,
            "--run-id",
            run_id,
            "--eval-id",
            "cli-metric",
            "--adapter",
            "metric_threshold",
            "--metric-name",
            "score",
            "--metric-value",
            "1.0",
            "--threshold",
            "0.5",
        )
        source = run_dir(root, goal_id, run_id) / "artifacts" / "deposition" / "cli-memory.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("problem\nevidence\nscope\nvalidation\nrollback\n", encoding="utf-8")
        self._cli(root, "promote", "--root", str(root), "--goal-id", goal_id, "--run-id", run_id, "--kind", "memory", "--name", "cli-memory", "--source-artifact", "artifacts/deposition/cli-memory.md")
        large = run_dir(root, goal_id, run_id) / "artifacts" / "cli-large.txt"
        large.write_text("x" * 32, encoding="utf-8")
        self._cli(root, "retention", "run", "--root", str(root), "--goal-id", goal_id, "--run-id", run_id, "--min-bytes", "8")
        conflict = root / "cli-conflict.txt"
        conflict.write_text("<<<<<<< ours\nleft\n=======\nright\n>>>>>>> theirs\n", encoding="utf-8")
        blocked = self._cli(root, "merge-repair", "--root", str(root), "--goal-id", goal_id, "--run-id", run_id, "--conflict-file", "cli-conflict.txt", "--apply")
        self.assertEqual(blocked["status"], "blocked")
        self._cli(root, "report-gui", "--root", str(root), "--goal-id", goal_id, "--run-id", run_id)
        data = generate_report(root, goal_id, run_id)
        event_types = {event["event_type"] for event in data["events"]}
        self.assertIn("notification_sent", event_types)
        self.assertIn("evaluation_recorded", event_types)
        self.assertIn("promotion_applied", event_types)
        self.assertIn("artifact_retained", event_types)
        self.assertIn("merge_repair_blocked", event_types)
        self.assertIn("report_gui_manifest_written", event_types)

    def _cli(self, cwd: Path, *args: str) -> dict:
        env = os.environ.copy()
        repo_root = Path(__file__).resolve().parents[1]
        env["PYTHONPATH"] = str(repo_root) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        proc = subprocess.run([sys.executable, "-m", "long_horizon", *args], cwd=cwd, env=env, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return json.loads(proc.stdout)


if __name__ == "__main__":
    unittest.main()
