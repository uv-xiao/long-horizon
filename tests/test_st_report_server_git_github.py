from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from urllib import request

from long_horizon.comments import inbox_dir
from long_horizon.goal import create_goal, create_run
from long_horizon.install import install
from long_horizon.io import read_json, read_jsonl, read_toml
from long_horizon.logger import append_event
from long_horizon.paths import run_dir
from long_horizon.process import create_process
from long_horizon.report import generate_report
from long_horizon.report_server import ReportServer
from long_horizon.git_adapter import import_child_state, merge_child_branch, spawn_child_worktree
from long_horizon.github_adapter import GitHubAdapter, github_comment_envelope


class ReportServerGitGithubSystemTests(unittest.TestCase):
    def make_git_run(self) -> tuple[Path, str, str]:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "repo"
        root.mkdir()
        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
        (root / "README.md").write_text("# Target\n", encoding="utf-8")
        install(root, apply=True)
        subprocess.run(["git", "add", "README.md", ".gitignore", "AGENTS.md", ".agents"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        contract = root / "contract.md"
        contract.write_text("# Contract\n", encoding="utf-8")
        create_goal(root, "goal-st", contract)
        create_run(root, "goal-st", "run-1")
        return root, "goal-st", "run-1"

    def test_report_generate_writes_timeline_and_server_imports_pushed_human_comment(self):
        root, goal_id, run_id = self.make_git_run()
        create_process(root, goal_id, run_id, "child-a", role="task", parent_process_id="primary")
        append_event(root, goal_id, run_id, "commands", "check_result", {"check_id": "seed", "status": "passed"})
        data = generate_report(root, goal_id, run_id)
        reports = run_dir(root, goal_id, run_id) / "reports"
        self.assertTrue((reports / "progress.html").exists())
        self.assertIn("timeline", data)
        self.assertTrue(any(lane["lane_id"] == "process:child-a" for lane in data["timeline"]["lanes"]))
        self.assertTrue(any(message["kind"] == "spawn" and message["to_lane_id"] == "process:child-a" for message in data["timeline"]["messages"]))
        self.assertTrue(any(marker["event_type"] == "check_result" for marker in data["timeline"]["event_markers"]))
        self.assertFalse((reports / "slides.html").exists())
        self.assertFalse((reports / "slides-data.json").exists())
        self.assertIn("feature_settings", data)
        self.assertIn("mailboxes", data)

        with ReportServer(root, goal_id, run_id, host="127.0.0.1", port=0) as server:
            base = server.url
            html = request.urlopen(f"{base}/progress.html", timeout=5).read().decode("utf-8")
            self.assertIn("perfetto-timeline", html)
            self.assertIn("timeline-state-segment", html)
            self.assertIn("timeline-event-marker", html)
            self.assertIn("timeline-message-link", html)
            self.assertIn("state-transition-diagram", html)
            self.assertIn("child-a", html)
            self.assertIn("check_result", html)
            self.assertIn('<script id="report-data" type="application/json">{"goal_id"', html)
            body = json.dumps(
                {
                    "channel": "github",
                    "external_comment_id": "review-17",
                    "external_thread_id": "pr-9",
                    "author": "reviewer",
                    "target_refs": ["#process-child-a"],
                    "body": "request change: child-a must follow watchdog steering now",
                }
            ).encode("utf-8")
            req = request.Request(f"{base}/comments", data=body, method="POST", headers={"Content-Type": "application/json"})
            response = json.loads(request.urlopen(req, timeout=5).read().decode("utf-8"))
            self.assertEqual(response["imported_count"], 1)
            served = json.loads(request.urlopen(f"{base}/report-data.json", timeout=5).read().decode("utf-8"))
            self.assertTrue(any(event["event_type"] == "human_comment" for event in served["events"]))
            self.assertTrue(any(comment["classification"] == "request_change" for comment in served["human_comments"]))
            self.assertTrue(any(marker["event_type"] == "human_comment" for marker in served["timeline"]["event_markers"]))
            self.assertTrue(any(message["kind"] == "human_comment" for message in served["timeline"]["messages"]))

    def test_real_git_worktree_spawn_copies_long_horizon_state_then_parent_imports_child_artifact(self):
        root, goal_id, run_id = self.make_git_run()
        worktree_path = root.parent / "repo-child-fast"
        child = spawn_child_worktree(
            root,
            goal_id,
            run_id,
            parent_process_id="primary",
            process_id="candidate-fast",
            branch="lh/candidate-fast",
            worktree_path=worktree_path,
        )
        self.assertTrue(worktree_path.exists())
        self.assertTrue((worktree_path / ".long-horizon" / "goals" / goal_id / "runs" / run_id).exists())
        self.assertEqual(read_toml(child["parent_process_path"])["worktree_path"], str(worktree_path.resolve()))
        subprocess.run(["git", "branch", "--show-current"], cwd=worktree_path, check=True, stdout=subprocess.PIPE, text=True)

        child_run = run_dir(worktree_path, goal_id, run_id)
        child_artifact = child_run / "artifacts" / "candidates" / "fast.md"
        child_artifact.parent.mkdir(parents=True, exist_ok=True)
        child_artifact.write_text("fast candidate result\n", encoding="utf-8")
        append_event(
            worktree_path,
            goal_id,
            run_id,
            "artifacts",
            "artifact_created",
            {"artifact_id": "fast", "path": "artifacts/candidates/fast.md"},
            process_id="candidate-fast",
        )
        parent_artifact_log_before = read_jsonl(run_dir(root, goal_id, run_id) / "logs" / "artifacts.jsonl")
        self.assertFalse(any(event["event_type"] == "artifact_created" for event in parent_artifact_log_before))

        imported = import_child_state(
            root,
            goal_id,
            run_id,
            child_worktree_path=worktree_path,
            child_process_id="candidate-fast",
            artifact_paths=["artifacts/candidates/fast.md"],
            target_process_id="primary",
        )
        copied = run_dir(root, goal_id, run_id) / imported["copied_artifacts"][0]
        self.assertTrue(copied.exists())
        self.assertIn("fast candidate", copied.read_text(encoding="utf-8"))
        parent_events = read_jsonl(run_dir(root, goal_id, run_id) / "logs" / "artifacts.jsonl")
        self.assertTrue(any(event["event_type"] == "artifact_imported" for event in parent_events))
        child_events = read_jsonl(child_run / "logs" / "artifacts.jsonl")
        self.assertTrue(any(event["event_type"] == "artifact_created" for event in child_events))

    def test_parent_can_merge_child_branch_after_worktree_exploration(self):
        root, goal_id, run_id = self.make_git_run()
        worktree_path = root.parent / "repo-child-merge"
        spawn_child_worktree(
            root,
            goal_id,
            run_id,
            parent_process_id="primary",
            process_id="candidate-merge",
            branch="lh/candidate-merge",
            worktree_path=worktree_path,
        )
        (worktree_path / "feature.txt").write_text("merged child branch output\n", encoding="utf-8")
        subprocess.run(["git", "add", "feature.txt"], cwd=worktree_path, check=True)
        subprocess.run(["git", "commit", "-m", "child feature"], cwd=worktree_path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        result = merge_child_branch(
            root,
            goal_id,
            run_id,
            child_process_id="candidate-merge",
            branch="lh/candidate-merge",
            target_process_id="primary",
        )
        self.assertEqual(result["status"], "merged")
        self.assertEqual((root / "feature.txt").read_text(encoding="utf-8"), "merged child branch output\n")
        merge_artifact = run_dir(root, goal_id, run_id) / "artifacts" / "process-merges" / "candidate-merge-merge.md"
        self.assertTrue(merge_artifact.exists())
        self.assertIn("candidate-merge", merge_artifact.read_text(encoding="utf-8"))
        self.assertEqual(result["merge_artifact"], "artifacts/process-merges/candidate-merge-merge.md")
        events = read_jsonl(run_dir(root, goal_id, run_id) / "logs" / "process-events.jsonl")
        self.assertTrue(any(event["event_type"] == "child_branch_merged" for event in events))

    def test_github_adapter_uses_repo_local_auth_and_normalizes_review_comments(self):
        repo = Path(__file__).resolve().parents[1]
        if not shutil.which("gh") or not ((repo / "tmp" / "gh" / "hosts.yml").exists() or (repo / ".gh" / "hosts.yml").exists()):
            self.skipTest("repo-local gh auth is unavailable")
        adapter = GitHubAdapter(repo)
        self.assertIn(adapter.auth_dir.name, {".gh", "gh"})
        envelope = github_comment_envelope(
            channel="github",
            comment_id="discussion-42",
            thread_id="pull-1",
            author="reviewer",
            body="approve: report serve path follows the process model",
            target_refs=["plan_accepted", "#process-primary"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            install(root, apply=True)
            contract = root / "contract.md"
            contract.write_text("# Contract\n", encoding="utf-8")
            create_goal(root, "goal-gh", contract)
            create_run(root, "goal-gh", "run-1")
            adapter.write_comment_envelope(root, envelope)
            self.assertTrue(list(inbox_dir(root).glob("github-discussion-42.json")))

        info = adapter.repo_info()
        self.assertIn("nameWithOwner", info)
        self.assertTrue(info["nameWithOwner"].endswith("/long-horizon"))


if __name__ == "__main__":
    unittest.main()
