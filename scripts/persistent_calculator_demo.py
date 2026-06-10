from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEMO_ROOT = REPO_ROOT.parent / "long-horizon-calculator-demo"
PARENT_BRANCH = "lh/demo/calculator-parent"
GOAL_ID = "calculator-shortest"
RUN_ID = "run-1"

LANGUAGES = [
    {
        "process_id": "candidate-python",
        "language": "python",
        "branch": "lh/demo/calculator-python",
        "file": "calc.py",
        "run": [sys.executable, "calc.py"],
        "wait": "candidate_python_done",
    },
    {
        "process_id": "candidate-node",
        "language": "javascript",
        "branch": "lh/demo/calculator-node",
        "file": "calc.js",
        "run": ["node", "calc.js"],
        "wait": "candidate_node_done",
    },
    {
        "process_id": "candidate-perl",
        "language": "perl",
        "branch": "lh/demo/calculator-perl",
        "file": "calc.pl",
        "run": ["perl", "calc.pl"],
        "wait": "candidate_perl_done",
    },
]

EXPRESSIONS = [
    ("1+2*3", 7.0),
    ("(8-3)/5", 1.0),
    ("2**3+4", 12.0),
    ("-3+10/2", 2.0),
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Persistent long-horizon calculator demo")
    parser.add_argument("--demo-root", default=str(DEFAULT_DEMO_ROOT), help="directory that stores persistent demo worktrees")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="create and execute the persistent demo")
    run.add_argument("--reset", action="store_true", help="remove existing demo branches/worktrees first")
    run.add_argument("--use-codex", action="store_true", help="use codex exec to write candidate programs")
    sub.add_parser("status", help="print persistent demo branches, paths, and key artifacts")
    sub.add_parser("clean", help="remove persistent demo worktrees and branches")
    args = parser.parse_args(argv)
    demo_root = Path(args.demo_root).resolve()
    if args.cmd == "clean":
        clean(demo_root)
        return 0
    if args.cmd == "status":
        print_status(demo_root)
        return 0
    if args.reset:
        clean(demo_root)
    run_demo(demo_root, use_codex=args.use_codex)
    return 0


def run_demo(demo_root: Path, use_codex: bool) -> None:
    ensure_clean_repo()
    if demo_root.exists():
        raise SystemExit(f"demo root already exists: {demo_root}\nRun: python scripts/persistent_calculator_demo.py --demo-root {demo_root} clean")
    parent = demo_root / "parent"
    worktrees = demo_root / "worktrees"
    artifacts = demo_root / "host-artifacts"
    worktrees.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir(parents=True, exist_ok=True)
    git("worktree", "add", "-b", PARENT_BRANCH, str(parent), "HEAD")

    sys.path.insert(0, str(REPO_ROOT))
    from long_horizon.comments import import_comments, inbox_dir
    from long_horizon.git_adapter import import_child_state, merge_child_branch, spawn_child_worktree
    from long_horizon.goal import create_goal, create_run
    from long_horizon.install import install
    from long_horizon.io import read_toml, write_json, write_text, write_toml
    from long_horizon.logger import append_event
    from long_horizon.observer import create_observer, record_intervention
    from long_horizon.paths import boards_dir, run_dir
    from long_horizon.report import generate_report
    from long_horizon.transition import transition
    from long_horizon.workflow import allowed_next

    install(parent, apply=True)
    commit_if_dirty(parent, "demo: install long-horizon runtime")
    contract_file = artifacts / "calculator-contract.md"
    contract_file.write_text(_contract_text(), encoding="utf-8")
    create_goal(parent, GOAL_ID, contract_file)
    create_run(parent, GOAL_ID, RUN_ID)
    flow = _calculator_flow()
    write_toml(run_dir(parent, GOAL_ID, RUN_ID) / "flow.snapshot.toml", flow)
    board = read_toml(boards_dir(parent, GOAL_ID, RUN_ID) / "task.toml")
    board["current_state"] = "plan_acceptance"
    board["allowed_next"] = allowed_next(flow, "plan_acceptance")
    write_toml(boards_dir(parent, GOAL_ID, RUN_ID) / "task.toml", board)
    create_observer(parent, GOAL_ID, RUN_ID, "calculator-watchdog", ["primary"] + [item["process_id"] for item in LANGUAGES], [item["process_id"] for item in LANGUAGES])
    write_text(run_dir(parent, GOAL_ID, RUN_ID) / "artifacts" / "plan.md", _plan_text(use_codex))
    write_json(
        inbox_dir(parent) / "local-plan-accepted.json",
        {
            "channel": "local",
            "external_comment_id": "plan-accepted",
            "external_thread_id": "calculator-demo",
            "author": "human-reviewer",
            "target_refs": ["plan_accepted"],
            "body": "approve persistent calculator demo plan",
        },
    )
    import_comments(parent, GOAL_ID, RUN_ID)
    require_applied(transition(parent, GOAL_ID, RUN_ID, "primary", "candidate_iteration_1"))

    results: list[dict[str, Any]] = []
    for index, item in enumerate(LANGUAGES, start=1):
        child_path = worktrees / item["process_id"]
        spawn_child_worktree(parent, GOAL_ID, RUN_ID, "primary", item["process_id"], item["branch"], child_path)
        agent_log = artifacts / f"{item['process_id']}-codex-output.md"
        if use_codex:
            codex_generate_candidate(child_path, item, agent_log)
        else:
            deterministic_candidate(child_path, item, agent_log)
        result = evaluate_candidate(child_path, item)
        results.append(result)
        child_run = run_dir(child_path, GOAL_ID, RUN_ID)
        candidate_artifact = child_run / "artifacts" / "candidates" / f"{item['process_id']}.md"
        eval_artifact = child_run / "artifacts" / "evaluations" / f"{item['process_id']}.json"
        adapter_artifact = child_run / "artifacts" / "adapters" / f"codex-{item['process_id']}.md"
        write_text(candidate_artifact, candidate_summary(item, result, use_codex, agent_log))
        write_json(eval_artifact, result)
        write_text(adapter_artifact, adapter_summary(item, use_codex, agent_log))
        append_event(child_path, GOAL_ID, RUN_ID, "artifacts", "artifact_created", {"artifact_id": item["process_id"], "path": f"artifacts/candidates/{item['process_id']}.md"}, process_id=item["process_id"])
        append_event(child_path, GOAL_ID, RUN_ID, "commands", "check_result", {"check_id": f"{item['process_id']}_tests_passed", "status": "passed" if result["passed"] else "failed"}, process_id=item["process_id"])
        append_event(child_path, GOAL_ID, RUN_ID, "process-events", "process_completed", {"wait_refs": [item["wait"]], "result": result}, process_id=item["process_id"])
        commit_child(child_path, item, result)
        import_child_state(parent, GOAL_ID, RUN_ID, child_path, item["process_id"], [f"artifacts/candidates/{item['process_id']}.md", f"artifacts/evaluations/{item['process_id']}.json", f"artifacts/adapters/codex-{item['process_id']}.md"])
        append_event(parent, GOAL_ID, RUN_ID, "process-events", "process_completed", {"wait_refs": [item["wait"]], "source": "parent_join_after_import", "result": result}, process_id=item["process_id"])
        record_intervention(parent, GOAL_ID, RUN_ID, "calculator-watchdog", item["process_id"], f"iteration {index}: verify shortest passing calculator candidate in {item['language']}")
        next_state = f"candidate_iteration_{index + 1}" if index < len(LANGUAGES) else "merge_selection"
        require_applied(transition(parent, GOAL_ID, RUN_ID, "primary", next_state))

    selected = select_shortest_passing(results)
    selection_path = run_dir(parent, GOAL_ID, RUN_ID) / "artifacts" / "selection" / "selected-candidate.json"
    write_json(selection_path, selected)
    append_event(parent, GOAL_ID, RUN_ID, "commands", "check_result", {"check_id": "selected_candidate_tests_passed", "status": "passed", "selected_process_id": selected["process_id"]})
    append_event(parent, GOAL_ID, RUN_ID, "artifacts", "candidate_selected", {"selected_process_id": selected["process_id"], "language": selected["language"], "bytes": selected["bytes"], "path": "artifacts/selection/selected-candidate.json"})
    merge_result = merge_child_branch(parent, GOAL_ID, RUN_ID, selected["process_id"], selected["branch"], "primary")
    merge_note = run_dir(parent, GOAL_ID, RUN_ID) / "artifacts" / "process-merges" / f"{selected['process_id']}-workflow-merge.md"
    write_text(merge_note, workflow_merge_note(selected, merge_result, results))
    require_applied(transition(parent, GOAL_ID, RUN_ID, "primary", "final_audit"))
    final_eval = evaluate_candidate(parent, selected)
    write_json(run_dir(parent, GOAL_ID, RUN_ID) / "artifacts" / "evaluations" / "final-parent-evaluation.json", final_eval)
    append_event(parent, GOAL_ID, RUN_ID, "commands", "check_result", {"check_id": "final_parent_tests_passed", "status": "passed" if final_eval["passed"] else "failed"})
    write_json(
        inbox_dir(parent) / "local-final-accepted.json",
        {
            "channel": "local",
            "external_comment_id": "final-accepted",
            "external_thread_id": "calculator-demo",
            "author": "human-reviewer",
            "target_refs": ["final_acceptance", f"#process-{selected['process_id']}"],
            "body": f"approve final calculator candidate from {selected['process_id']}",
        },
    )
    import_comments(parent, GOAL_ID, RUN_ID)
    require_applied(transition(parent, GOAL_ID, RUN_ID, "primary", "completed"))
    report = generate_report(parent, GOAL_ID, RUN_ID)
    write_json(demo_root / "demo-summary.json", {
        "demo_root": str(demo_root),
        "parent_worktree": str(parent),
        "parent_branch": PARENT_BRANCH,
        "goal_id": GOAL_ID,
        "run_id": RUN_ID,
        "selected": selected,
        "events": len(report["events"]),
        "report": str(run_dir(parent, GOAL_ID, RUN_ID) / "reports" / "progress.html"),
        "slides": str(run_dir(parent, GOAL_ID, RUN_ID) / "reports" / "slides.html"),
        "cleanup": f"python scripts/persistent_calculator_demo.py --demo-root {demo_root} clean",
    })
    print_status(demo_root)


def clean(demo_root: Path) -> None:
    for path in [
        demo_root / "worktrees" / "candidate-python",
        demo_root / "worktrees" / "candidate-node",
        demo_root / "worktrees" / "candidate-perl",
        demo_root / "parent",
    ]:
        if path.exists():
            subprocess.run(["git", "worktree", "remove", "--force", str(path)], cwd=REPO_ROOT, check=False)
    subprocess.run(["git", "worktree", "prune"], cwd=REPO_ROOT, check=False)
    for branch in [item["branch"] for item in LANGUAGES] + [PARENT_BRANCH]:
        subprocess.run(["git", "branch", "-D", branch], cwd=REPO_ROOT, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if demo_root.exists():
        shutil.rmtree(demo_root)


def print_status(demo_root: Path) -> None:
    summary = demo_root / "demo-summary.json"
    print(f"demo_root: {demo_root}")
    print(f"parent_worktree: {demo_root / 'parent'}")
    print(f"parent_branch: {PARENT_BRANCH}")
    print("child_branches:")
    for item in LANGUAGES:
        print(f"  - {item['branch']} -> {demo_root / 'worktrees' / item['process_id']}")
    if summary.exists():
        print(summary.read_text(encoding="utf-8"))
    print("inspect:")
    print(f"  open {demo_root / 'parent' / '.long-horizon' / 'goals' / GOAL_ID / 'runs' / RUN_ID / 'reports' / 'progress.html'}")
    print(f"  open {demo_root / 'parent' / '.long-horizon' / 'goals' / GOAL_ID / 'runs' / RUN_ID / 'reports' / 'slides.html'}")
    print("clean:")
    print(f"  python scripts/persistent_calculator_demo.py --demo-root {demo_root} clean")


def codex_generate_candidate(child_path: Path, item: dict[str, Any], agent_log: Path) -> None:
    prompt = f"""Implement the shortest possible expression calculator in {item['language']}.

Create exactly one source file named {item['file']} in this working directory.
The program must read one expression string from stdin and print the numeric value.
It only needs to pass these expressions: {', '.join(expr for expr, _ in EXPRESSIONS)}.
Use the standard language runtime. Prefer the shortest source code that passes.
Do not modify any other tracked files. Do not commit.
"""
    cmd = [
        "codex",
        "exec",
        "--sandbox",
        "workspace-write",
        "-C",
        str(child_path),
        "--output-last-message",
        str(agent_log),
        prompt,
    ]
    proc = subprocess.run(cmd, cwd=child_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"codex failed for {item['process_id']}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    if not (child_path / item["file"]).exists():
        raise RuntimeError(f"codex did not create {item['file']} in {child_path}")


def deterministic_candidate(child_path: Path, item: dict[str, Any], agent_log: Path) -> None:
    fallback = {
        "python": "print(eval(input()))\n",
        "javascript": "console.log(eval(require('fs').readFileSync(0,'utf8')))\n",
        "perl": "print eval<>\n",
    }
    (child_path / item["file"]).write_text(fallback[item["language"]], encoding="utf-8")
    agent_log.write_text(f"Deterministic fallback wrote {item['file']} for {item['language']}.\n", encoding="utf-8")


def evaluate_candidate(root: Path, item: dict[str, Any]) -> dict[str, Any]:
    source = root / item["file"]
    if not source.exists():
        return {"process_id": item["process_id"], "language": item["language"], "branch": item["branch"], "file": item["file"], "passed": False, "bytes": 10**9, "cases": [{"error": "missing source"}]}
    cases = []
    passed = True
    for expr, expected in EXPRESSIONS:
        proc = subprocess.run(item["run"], cwd=root, input=expr + "\n", stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        try:
            actual = float(proc.stdout.strip())
        except ValueError:
            actual = None
        ok = proc.returncode == 0 and actual is not None and abs(actual - expected) < 1e-9
        passed = passed and ok
        cases.append({"expression": expr, "expected": expected, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip(), "returncode": proc.returncode, "passed": ok})
    return {"process_id": item["process_id"], "language": item["language"], "branch": item["branch"], "file": item["file"], "run": item["run"], "passed": passed, "bytes": len(source.read_bytes()), "cases": cases}


def commit_child(child_path: Path, item: dict[str, Any], result: dict[str, Any]) -> None:
    git_in(child_path, "add", item["file"])
    git_in(child_path, "commit", "-m", f"demo: {item['language']} calculator candidate")


def commit_if_dirty(path: Path, message: str) -> None:
    status = git_in(path, "status", "--short").strip()
    if not status:
        return
    git_in(path, "add", "AGENTS.md", ".gitignore", ".agents")
    if git_in(path, "status", "--short").strip():
        git_in(path, "commit", "-m", message)


def select_shortest_passing(results: list[dict[str, Any]]) -> dict[str, Any]:
    passing = [result for result in results if result["passed"]]
    if not passing:
        raise RuntimeError("no candidate passed calculator evaluation")
    return sorted(passing, key=lambda result: (result["bytes"], result["language"]))[0]


def _calculator_flow() -> dict[str, Any]:
    return {
        "flow": {"id": "calculator-shortest-humanize-v1", "initial_state": "plan_acceptance", "terminal_states": ["completed"]},
        "states": [
            {"id": "plan_acceptance", "kind": "human_gate"},
            {"id": "candidate_iteration_1", "kind": "parallel_inner_loop"},
            {"id": "candidate_iteration_2", "kind": "parallel_inner_loop"},
            {"id": "candidate_iteration_3", "kind": "parallel_inner_loop"},
            {"id": "merge_selection", "kind": "merge_gate"},
            {"id": "final_audit", "kind": "audit"},
            {"id": "completed", "kind": "terminal"},
        ],
        "transitions": [
            {"from": "plan_acceptance", "to": "candidate_iteration_1", "requires_human": True, "human_gate": "plan_accepted"},
            {"from": "candidate_iteration_1", "to": "candidate_iteration_2", "requires_waits": ["candidate_python_done"]},
            {"from": "candidate_iteration_2", "to": "candidate_iteration_3", "requires_waits": ["candidate_node_done"]},
            {"from": "candidate_iteration_3", "to": "merge_selection", "requires_waits": ["candidate_perl_done"]},
            {"from": "merge_selection", "to": "final_audit", "requires_artifacts": ["artifacts/selection/selected-candidate.json"], "requires_checks": ["selected_candidate_tests_passed"]},
            {"from": "final_audit", "to": "completed", "requires_human": True, "human_gate": "final_acceptance"},
        ],
        "merge_strategies": [
            {
                "id": "shortest_passing_calculator",
                "from_state": "merge_selection",
                "candidate_processes": [item["process_id"] for item in LANGUAGES],
                "selection_metric": "fewest_source_bytes_after_fixed_expression_tests",
                "repository_strategy": "merge_child_branch_no_ff",
                "workflow_imports": ["candidate_summary", "evaluation", "adapter_note", "process_merge_artifact"],
                "required_checks": ["selected_candidate_tests_passed"],
                "promotion_policy": "parent_selects_shortest_passing_candidate",
                "rejection_policy": "import compact summaries; leave full failed artifacts in child state",
            }
        ],
    }


def _contract_text() -> str:
    return """# Calculator Shortest Candidate Demo

Goal: produce the shortest passing expression calculator candidate.

Input: one expression string on stdin.
Output: numeric value on stdout.

Acceptance:
- pass fixed expression cases;
- run at least three inner-loop candidate iterations;
- try different languages in child worktrees;
- select the shortest passing source by byte length;
- merge selected repository content back to parent;
- preserve child state and merge evidence for human inspection.
"""


def _plan_text(use_codex: bool) -> str:
    mode = "Codex CLI candidate generation" if use_codex else "deterministic fallback candidate generation"
    return f"""# Plan

1. Human accepts the goal contract.
2. Spawn three child worktrees for Python, JavaScript, and Perl.
3. Use {mode} to create one calculator source file in each child.
4. Evaluate fixed expression cases and record per-candidate artifacts.
5. Import child summaries into parent state.
6. Select shortest passing candidate.
7. Merge selected child branch into parent and write workflow merge artifact.
8. Generate progress and slide reports for human inspection.
"""


def candidate_summary(item: dict[str, Any], result: dict[str, Any], use_codex: bool, agent_log: Path) -> str:
    return f"""# Candidate Summary

- process_id: `{item['process_id']}`
- language: `{item['language']}`
- branch: `{item['branch']}`
- file: `{item['file']}`
- generated_by: `{'codex exec' if use_codex else 'deterministic fallback'}`
- agent_log: `{agent_log}`
- passed: `{result['passed']}`
- source_bytes: `{result['bytes']}`

## Evaluation

```json
{json.dumps(result, indent=2, sort_keys=True)}
```
"""


def adapter_summary(item: dict[str, Any], use_codex: bool, agent_log: Path) -> str:
    return f"""# Adapter Note

- process_id: `{item['process_id']}`
- adapter: `codex exec`
- used: `{use_codex}`
- agent_log: `{agent_log}`

This demo records candidate generation as an agent substrate action. The
workflow state is still advanced only by long-horizon transition commands.
"""


def workflow_merge_note(selected: dict[str, Any], merge_result: dict[str, Any], results: list[dict[str, Any]]) -> str:
    rejected = [result for result in results if result["process_id"] != selected["process_id"]]
    return f"""# Workflow Merge Decision

- selected_process_id: `{selected['process_id']}`
- selected_language: `{selected['language']}`
- selected_branch: `{selected['branch']}`
- selected_source_bytes: `{selected['bytes']}`
- merge_status: `{merge_result['status']}`
- git_merge_artifact: `{merge_result.get('merge_artifact', '')}`

## Rationale

The selected candidate is the shortest source among fixed-expression candidates
that passed all evaluation cases.

## Rejected Candidates

```json
{json.dumps(rejected, indent=2, sort_keys=True)}
```
"""


def require_applied(result: dict[str, Any]) -> None:
    if result.get("status") != "applied":
        raise RuntimeError(f"transition failed: {result}")


def ensure_clean_repo() -> None:
    status = subprocess.run(["git", "status", "--short"], cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True).stdout.strip()
    if status:
        raise SystemExit(f"repository must be clean before running persistent demo:\n{status}")


def git(*args: str) -> str:
    return git_in(REPO_ROOT, *args)


def git_in(cwd: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {cwd}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    return proc.stdout


if __name__ == "__main__":
    raise SystemExit(main())
