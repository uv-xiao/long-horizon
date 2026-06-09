from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .capabilities import analyze_target, load_capabilities
from .comments import import_comments
from .config import load_config, set_config_value, validate_config
from .goal import create_goal, create_run
from .git_adapter import import_child_state, merge_child_branch, spawn_child_worktree
from .github_adapter import GitHubAdapter, record_github_operation
from .install import install
from .logger import append_event, append_loose
from .mailbox import ack_message, read_mailbox, send_message
from .observer import create_observer, record_intervention
from .process import create_process, heartbeat, interrupt, record_flow_amendment, resume
from .report import generate_report
from .report_server import ReportServer
from .task_setup import create_task_setup, initialize_task
from .transition import transition
from .validators import validate_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m long_horizon")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("install")
    p.add_argument("--target", required=True)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--target-agent", default="auto")
    p.add_argument("--operation-mode", choices=["runtime-owned", "native-agent", "hybrid"])
    p.add_argument("--force-analyze", action="store_true")

    p = sub.add_parser("capabilities")
    caps_sub = p.add_subparsers(dest="capabilities_cmd", required=True)
    cp = caps_sub.add_parser("analyze")
    cp.add_argument("--root", required=True)
    cp.add_argument("--target-agent", default="auto")
    cp.add_argument("--operation-mode", choices=["runtime-owned", "native-agent", "hybrid"])
    cp.add_argument("--force", action="store_true")
    cp = caps_sub.add_parser("show")
    cp.add_argument("--root", required=True)

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

    p = sub.add_parser("task")
    tsub = p.add_subparsers(dest="task_cmd", required=True)
    tp = tsub.add_parser("setup")
    tp.add_argument("--root", required=True)
    tp.add_argument("--request", required=True)
    tp.add_argument("--task-id")
    tp.add_argument("--target-agent", default="auto")
    tp.add_argument("--operation-mode", choices=["runtime-owned", "native-agent", "hybrid"])
    tp = tsub.add_parser("initialize")
    tp.add_argument("--root", required=True)
    tp.add_argument("--task-id", required=True)
    tp.add_argument("--goal-id", required=True)
    tp.add_argument("--run-id", required=True)
    tp.add_argument("--contract-text")

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
            pp.add_argument("--process-kind", choices=["workspace", "virtual"], default="workspace")
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
    pp = psub.add_parser("amend-flow")
    pp.add_argument("--root", required=True)
    pp.add_argument("--goal-id", required=True)
    pp.add_argument("--run-id", required=True)
    pp.add_argument("--owner-process-id", required=True)
    pp.add_argument("--target-process-id", required=True)
    pp.add_argument("--reason", required=True)
    pp.add_argument("--risk-class", default="normal")
    pp.add_argument("--approval-ref", action="append", default=[])
    pp.add_argument("--evidence-ref", action="append", default=[])
    pp.add_argument("--flow-patch-ref", default="")

    p = sub.add_parser("mailbox")
    msub = p.add_subparsers(dest="mailbox_cmd", required=True)
    mp = msub.add_parser("send")
    mp.add_argument("--root", required=True)
    mp.add_argument("--goal-id", required=True)
    mp.add_argument("--run-id", required=True)
    mp.add_argument("--source-process-id", required=True)
    mp.add_argument("--target-process-id", required=True)
    mp.add_argument("--message-type", required=True)
    mp.add_argument("--body", required=True)
    mp.add_argument("--artifact-ref", action="append", default=[])
    mp.add_argument("--causal-ref", action="append", default=[])
    mp.add_argument("--requires-ack", action="store_true")
    mp = msub.add_parser("list")
    mp.add_argument("--root", required=True)
    mp.add_argument("--goal-id", required=True)
    mp.add_argument("--run-id", required=True)
    mp.add_argument("--process-id", required=True)
    mp.add_argument("--box", choices=["inbox", "outbox", "ack"], default="inbox")
    mp = msub.add_parser("ack")
    mp.add_argument("--root", required=True)
    mp.add_argument("--goal-id", required=True)
    mp.add_argument("--run-id", required=True)
    mp.add_argument("--process-id", required=True)
    mp.add_argument("--message-id", required=True)
    mp.add_argument("--status", default="acknowledged")
    mp.add_argument("--body", default="")

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
    gp = ghsub.add_parser("operation")
    gp.add_argument("--root", required=True)
    gp.add_argument("--goal-id", required=True)
    gp.add_argument("--run-id", required=True)
    gp.add_argument("--operation", required=True)
    gp.add_argument("--target", choices=["issue", "pr"], required=True)
    gp.add_argument("--title", default="")
    gp.add_argument("--body", default="")
    gp.add_argument("--number", type=int)
    gp.add_argument("--head", default="")
    gp.add_argument("--base", default="")
    gp.add_argument("--process-id", default="github")
    gp.add_argument("--target-process-id", default="primary")
    gp.add_argument("--execute", action="store_true")

    args = parser.parse_args(argv)
    result = _dispatch(args)
    if result is not None:
        print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


def _dispatch(args: argparse.Namespace):
    if args.cmd == "install":
        return {
            "install_plan": str(
                install(
                    args.target,
                    apply=args.apply,
                    target_agent=args.target_agent,
                    operation_mode=args.operation_mode,
                    force_analyze=args.force_analyze,
                )
            )
        }
    if args.cmd == "capabilities":
        if args.capabilities_cmd == "analyze":
            return analyze_target(args.root, target_agent=args.target_agent, operation_mode=args.operation_mode, force=args.force)
        if args.capabilities_cmd == "show":
            return load_capabilities(args.root)
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
    if args.cmd == "task" and args.task_cmd == "setup":
        return create_task_setup(args.root, args.request, task_id=args.task_id, target_agent=args.target_agent, operation_mode=args.operation_mode)
    if args.cmd == "task" and args.task_cmd == "initialize":
        return initialize_task(args.root, args.task_id, args.goal_id, args.run_id, contract_text=args.contract_text)
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
            return {"process": str(create_process(args.root, args.goal_id, args.run_id, args.process_id, role=args.role, process_kind=args.process_kind))}
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
        if args.process_cmd == "amend-flow":
            return record_flow_amendment(
                args.root,
                args.goal_id,
                args.run_id,
                args.owner_process_id,
                args.target_process_id,
                args.reason,
                risk_class=args.risk_class,
                evidence_refs=args.evidence_ref,
                approval_refs=args.approval_ref,
                flow_patch_ref=args.flow_patch_ref,
            )
    if args.cmd == "mailbox":
        if args.mailbox_cmd == "send":
            return send_message(
                args.root,
                args.goal_id,
                args.run_id,
                args.source_process_id,
                args.target_process_id,
                args.message_type,
                args.body,
                artifact_refs=args.artifact_ref,
                causal_refs=args.causal_ref,
                requires_ack=args.requires_ack,
            )
        if args.mailbox_cmd == "list":
            return {"messages": read_mailbox(args.root, args.goal_id, args.run_id, args.process_id, args.box)}
        if args.mailbox_cmd == "ack":
            return ack_message(args.root, args.goal_id, args.run_id, args.process_id, args.message_id, status=args.status, body=args.body)
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
    if args.cmd == "github" and args.github_cmd == "operation":
        return record_github_operation(
            args.root,
            args.goal_id,
            args.run_id,
            args.operation,
            args.target,
            title=args.title,
            body=args.body,
            number=args.number,
            head=args.head,
            base=args.base,
            process_id=args.process_id,
            target_process_id=args.target_process_id,
            execute=args.execute,
        )
    raise SystemExit("unknown command")


def _payload(value: str) -> dict:
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)
