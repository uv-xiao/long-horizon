from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from long_horizon.capabilities import analyze_target
from long_horizon.goal import create_goal, create_run
from long_horizon.install import install
from long_horizon.io import read_json, read_toml
from long_horizon.paths import run_dir
from long_horizon.task_setup import create_task_setup


class V1TemplateUsabilitySystemTests(unittest.TestCase):
    def make_target(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "README.md").write_text("# Target\n", encoding="utf-8")
        return root

    def test_weak_agent_installs_runtime_owned_mode_and_phase_templates(self):
        root = self.make_target()
        plan = install(root)
        self.assertIn("Operation mode: `runtime-owned`", plan.read_text(encoding="utf-8"))
        install(root, apply=True)

        config = read_toml(root / ".long-horizon" / "config.toml")
        self.assertEqual(config["agent"]["operation_mode"], "runtime-owned")
        self.assertTrue((root / ".long-horizon" / "goals").exists())
        self.assertTrue((root / ".agents" / "skills" / "analyze-target-agent" / "SKILL.md").exists())
        self.assertTrue((root / ".agents" / "skills" / "complete-and-deposit" / "SKILL.md").exists())
        for prompt in [
            "target-analysis.md",
            "install-plan.md",
            "task-setup.md",
            "goal-contract.md",
            "flow-assembly.md",
            "execution-brief.md",
            "observer-intervention.md",
            "join-decision.md",
            "completion-audit.md",
            "deposition-review.md",
        ]:
            text = (root / ".agents" / "templates" / "long-horizon" / prompt).read_text(encoding="utf-8")
            self.assertIn("Hard Constraints", text)
            self.assertIn("Sequential Phases", text)

        task = create_task_setup(root, "Implement a small feature")
        self.assertEqual(task["operation_mode"], "runtime-owned")
        task_dir = Path(task["task_dir"])
        self.assertIn("Operation mode: `runtime-owned`", (task_dir / "setup.md").read_text(encoding="utf-8"))
        self.assertTrue((task_dir / "goal-contract.scaffold.md").exists())
        self.assertTrue((task_dir / "flow-plan.md").exists())
        self.assertTrue((task_dir / "execution-brief.md").exists())

    def test_strong_native_agent_uses_native_agent_mode_without_competing_loop(self):
        root = self.make_target()
        (root / ".claude").mkdir()
        (root / ".claude" / "CLAUDE.md").write_text(
            "Native loop with hooks, stop hook, subagents, Task tool, codex review, process session controls.\n",
            encoding="utf-8",
        )
        (root / ".claude" / "hooks.json").write_text('{"Stop": "native"}\n', encoding="utf-8")

        plan = install(root, target_agent="claude-code")
        plan_text = plan.read_text(encoding="utf-8")
        self.assertIn("Operation mode: `native-agent`", plan_text)
        self.assertIn("instead of duplicating", plan_text)
        install(root, apply=True, target_agent="claude-code")

        config = read_toml(root / ".long-horizon" / "config.toml")
        self.assertEqual(config["agent"]["operation_mode"], "native-agent")
        decision = (root / ".long-horizon" / "decisions" / "operation-mode.md").read_text(encoding="utf-8")
        self.assertIn("Selected mode: `native-agent`", decision)
        task = create_task_setup(root, "Run review-only audit", target_agent="claude-code")
        self.assertEqual(task["operation_mode"], "native-agent")
        self.assertEqual(task["profile"], "review-only")
        brief = (Path(task["task_dir"]) / "execution-brief.md").read_text(encoding="utf-8")
        self.assertIn("Mode: `native-agent`", brief)
        self.assertIn("Do not let prompts", brief)

    def test_capability_cache_reuses_and_invalidates_on_agent_surface_change(self):
        root = self.make_target()
        first = analyze_target(root, target_agent="manual", force=True)
        self.assertEqual(first["analysis"]["cache_status"], "refreshed")
        second = analyze_target(root, target_agent="manual")
        self.assertEqual(second["analysis"]["cache_status"], "reused")
        (root / "AGENTS.md").write_text("New agent rules with hooks and review.\n", encoding="utf-8")
        third = analyze_target(root, target_agent="manual")
        self.assertEqual(third["analysis"]["cache_status"], "refreshed")
        self.assertNotEqual(first["analysis"]["fingerprint"], third["analysis"]["fingerprint"])

    def test_report_and_agent_brief_include_operation_mode_provenance(self):
        root = self.make_target()
        install(root, apply=True, target_agent="codex-goal")
        contract = root / "contract.md"
        contract.write_text("# Contract\n\nGoal: prove operation mode\n", encoding="utf-8")
        create_goal(root, "goal-v1-usability", contract)
        create_run(root, "goal-v1-usability", "run-v1-usability")

        reports = run_dir(root, "goal-v1-usability", "run-v1-usability") / "reports"
        data = read_json(reports / "report-data.json")
        self.assertEqual(data["operation_mode"], "hybrid")
        self.assertIn("agent_capabilities", data)
        brief = (reports / "agent-brief.md").read_text(encoding="utf-8")
        self.assertIn("Operation mode: `hybrid`", brief)
        self.assertIn("Operation Mode Responsibilities", brief)
        html = (reports / "progress.html").read_text(encoding="utf-8")
        self.assertIn("Mode hybrid", html)


if __name__ == "__main__":
    unittest.main()
