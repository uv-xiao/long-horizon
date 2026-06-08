from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .comments import import_comments
from .config import load_config, set_config_value, validate_config
from .goal import create_goal, create_run
from .git_adapter import import_child_state, merge_child_branch, spawn_child_worktree
from .github_adapter import GitHubAdapter
from .install import install
from .logger import append_event, append_loose
from .observer import create_observer, record_intervention
from .process import create_process, heartbeat, interrupt, resume
from .report import generate_report
from .report_server import ReportServer
from .transition import transition
from .validators import validate_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m long_horizon")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("install")
    p.add_argument("--target", required=True)
    p.add_argument("--apply", action="store_true")

    p = sub.add_parser("config")
    csub = p.add_subparsers(dest="config_cmd", required=True)
    for name in ["show", "validate"]:
        cp = csub.add_parser(name)
        cp.add_argument("--root", required=True)
    cp = csub.add_parser("set")
    cp.add_argument("--root", required=True)
    cp.add_argument("key")
    cp.add_argument("value")

    p = sub.add_parser("goal")
    gsub = p.add_subparsers(dest="goal_cmd", required=True)
    gp = gsub.add_parser("create")
    gp.add_argument("--root", required=True)
    gp.add_argument("--goal-id", required=True)
    gp.add_argument("--contract", required=True)

    p = sub.add_parser("run")
    rsub = p.add_subparsers(dest="run_cmd", required=True)
    rp = rsub.add_parser("create")
    rp.add_argument("--root", required=True)
    rp.add_argument("--goal-id", required=True)
    rp.add_argument("--run-id", required=True)

    p = sub.add_parser("validate")
    p.add_argument("--root", required=True)
    p.add_argument("--goal-id")
    p.add_argument("--run-id")

    p = sub.add_parser("log")
    lsub = p.add_subparsers(dest="log_cmd", required=True)
    lp = lsub.add_parser("append")
    lp.add_argument("--root", required=True)
    lp.add_argument("--goal-id", required=True)
    lp.add_argument("--run-id", required=True)
    lp.add_argument("--ledger", required=True)
    lp.add_argument("--event-type", required=True)
    lp.add_argument("--payload", required=True)
    lp.add_argument("--process-id", default="primary")
    lp = lsub.add_parser("loose")
    lp.add_argument("--root", required=True)
    lp.add_argument("--goal-id", required=True)
    lp.add_argument("--run-id", required=True)
    lp.add_argument("--body", required=True)
    lp.add_argument("--process-id", default="primary")

    p = sub.add_parser("transition")
    p.add_argument("--root", required=True)
    p.add_argument("--goal-id", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--process-id", required=True)
    p.add_argument("--to", required=True)

    p = sub.add_parser("process")
    psub = p.add_subparsers(dest="process_cmd", required=True)
    for name in ["create", "heartbeat", "interrupt", "resume"]:
        pp = psub.add_parser(name)
        pp.add_argument("--root", required=True)
        pp.add_argument("--goal-id", required=True)
        pp.add_argument("--run-id", required=True)
        pp.add_argument("--process-id", required=True)
        if name == "create":
            pp.add_argument("--role", default="task")
        if name == "interrupt":
            pp.add_argument("--reason", required=True)
        if name == "resume":
            pp.add_argument("--new-session", required=True)
    pp = psub.add_parser("spawn-child-worktree")
    pp.add_argument("--root", required=True)
    pp.add_argument("--goal-id", required=True)
    pp.add_argument("--run-id", required=True)
    pp.add_argument("--parent-process-id", required=True)
    pp.add_argument("--process-id", required=True)
    pp.add_argument("--branch", required=True)
    pp.add_argument("--worktree-path", required=True)
    pp = psub.add_parser("import-child")
    pp.add_argument("--root", required=True)
    pp.add_argument("--goal-id", required=True)
    pp.add_argument("--run-id", required=True)
    pp.add_argument("--child-worktree-path", required=True)
    pp.add_argument("--child-process-id", required=True)
    pp.add_argument("--artifact-path", action="append", default=[])
    pp.add_argument("--target-process-id", default="primary")
    pp = psub.add_parser("merge-child-branch")
    pp.add_argument("--root", required=True)
    pp.add_argument("--goal-id", required=True)
    pp.add_argument("--run-id", required=True)
    pp.add_argument("--child-process-id", required=True)
    pp.add_argument("--branch", required=True)
    pp.add_argument("--target-process-id", default="primary")

    p = sub.add_parser("observer")
    osub = p.add_subparsers(dest="observer_cmd", required=True)
    op = osub.add_parser("create")
    op.add_argument("--root", required=True)
    op.add_argument("--goal-id", required=True)
    op.add_argument("--run-id", required=True)
    op.add_argument("--process-id", required=True)
    op.add_argument("--observe-target", action="append", default=[])
    op = osub.add_parser("intervene")
    op.add_argument("--root", required=True)
    op.add_argument("--goal-id", required=True)
    op.add_argument("--run-id", required=True)
    op.add_argument("--observer-id", required=True)
    op.add_argument("--target-process-id", required=True)
    op.add_argument("--message", required=True)

    p = sub.add_parser("report")
    repsub = p.add_subparsers(dest="report_cmd", required=True)
    rp = repsub.add_parser("generate")
    rp.add_argument("--root", required=True)
    rp.add_argument("--goal-id", required=True)
    rp.add_argument("--run-id", required=True)
    rp = repsub.add_parser("serve")
    rp.add_argument("--root", required=True)
    rp.add_argument("--goal-id", required=True)
    rp.add_argument("--run-id", required=True)
    rp.add_argument("--host", default="127.0.0.1")
    rp.add_argument("--port", type=int, default=8765)

    p = sub.add_parser("comments")
    csub = p.add_subparsers(dest="comments_cmd", required=True)
    cp = csub.add_parser("import")
    cp.add_argument("--root", required=True)
    cp.add_argument("--goal-id", required=True)
    cp.add_argument("--run-id", required=True)

    p = sub.add_parser("github")
    ghsub = p.add_subparsers(dest="github_cmd", required=True)
    gp = ghsub.add_parser("repo-info")
    gp.add_argument("--root", required=True)

    args = parser.parse_args(argv)
    result = _dispatch(args)
    if result is not None:
        print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


def _dispatch(args: argparse.Namespace):
    if args.cmd == "install":
        return {"install_plan": str(install(args.target, apply=args.apply))}
    if args.cmd == "config":
        if args.config_cmd == "show":
            return load_config(args.root)
        if args.config_cmd == "validate":
            errors = validate_config(args.root)
            if errors:
                raise SystemExit("\n".join(errors))
            return {"valid": True}
        if args.config_cmd == "set":
            return set_config_value(args.root, args.key, args.value)
    if args.cmd == "goal" and args.goal_cmd == "create":
        return {"goal_dir": str(create_goal(args.root, args.goal_id, args.contract))}
    if args.cmd == "run" and args.run_cmd == "create":
        return {"run_dir": str(create_run(args.root, args.goal_id, args.run_id))}
    if args.cmd == "validate":
        errors = validate_root(args.root, args.goal_id, args.run_id)
        if errors:
            raise SystemExit("\n".join(errors))
        return {"valid": True}
    if args.cmd == "log":
        if args.log_cmd == "append":
            payload = _payload(args.payload)
            return append_event(args.root, args.goal_id, args.run_id, args.ledger, args.event_type, payload, process_id=args.process_id)
        return append_loose(args.root, args.goal_id, args.run_id, args.body, process_id=args.process_id)
    if args.cmd == "transition":
        return transition(args.root, args.goal_id, args.run_id, args.process_id, args.to)
    if args.cmd == "process":
        if args.process_cmd == "create":
            return {"process": str(create_process(args.root, args.goal_id, args.run_id, args.process_id, role=args.role))}
        if args.process_cmd == "heartbeat":
            heartbeat(args.root, args.goal_id, args.run_id, args.process_id)
            return {"heartbeat": args.process_id}
        if args.process_cmd == "interrupt":
            interrupt(args.root, args.goal_id, args.run_id, args.process_id, args.reason)
            return {"interrupted": args.process_id}
        if args.process_cmd == "resume":
            resume(args.root, args.goal_id, args.run_id, args.process_id, args.new_session)
            return {"resumed": args.process_id}
        if args.process_cmd == "spawn-child-worktree":
            return spawn_child_worktree(args.root, args.goal_id, args.run_id, args.parent_process_id, args.process_id, args.branch, args.worktree_path)
        if args.process_cmd == "import-child":
            return import_child_state(
                args.root,
                args.goal_id,
                args.run_id,
                child_worktree_path=args.child_worktree_path,
                child_process_id=args.child_process_id,
                artifact_paths=args.artifact_path,
                target_process_id=args.target_process_id,
            )
        if args.process_cmd == "merge-child-branch":
            return merge_child_branch(args.root, args.goal_id, args.run_id, args.child_process_id, args.branch, args.target_process_id)
    if args.cmd == "observer":
        if args.observer_cmd == "create":
            return {"observer": str(create_observer(args.root, args.goal_id, args.run_id, args.process_id, args.observe_target))}
        return record_intervention(args.root, args.goal_id, args.run_id, args.observer_id, args.target_process_id, args.message)
    if args.cmd == "report":
        if args.report_cmd == "generate":
            return generate_report(args.root, args.goal_id, args.run_id)
        if args.report_cmd == "serve":
            ReportServer(args.root, args.goal_id, args.run_id, args.host, args.port).serve_forever()
            return None
    if args.cmd == "comments" and args.comments_cmd == "import":
        return {"imported": import_comments(args.root, args.goal_id, args.run_id)}
    if args.cmd == "github" and args.github_cmd == "repo-info":
        return GitHubAdapter(args.root).repo_info()
    raise SystemExit("unknown command")


def _payload(value: str) -> dict:
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)
