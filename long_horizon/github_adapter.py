from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .comments import inbox_dir
from .io import write_json
from .mailbox import send_message
from .process import create_process
from .paths import process_metadata_path
from .time import now_iso


SETUP_SCRIPT = """mkdir -p tmp/gh
export GH_CONFIG_DIR="$PWD/tmp/gh"
gh auth login --hostname github.com --git-protocol https --web
gh auth status
"""


class GitHubAdapter:
    def __init__(self, repo_root: str | Path, require_auth: bool = False):
        self.repo_root = Path(repo_root).resolve()
        self.auth_dir = self._detect_auth_dir() if require_auth else self._find_auth_dir()

    def repo_info(self) -> dict[str, Any]:
        self.verify_auth()
        return self._gh_json("repo", "view", "--json", "nameWithOwner,url")

    def operation_envelope(
        self,
        operation: str,
        target: str,
        title: str = "",
        body: str = "",
        number: int | None = None,
        head: str = "",
        base: str = "",
        execute: bool = False,
    ) -> dict[str, Any]:
        envelope = {
            "channel": "github",
            "operation": operation,
            "target": target,
            "title": title,
            "body": body,
            "number": number,
            "head": head,
            "base": base,
            "execute": execute,
            "created_at": now_iso(),
            "status": "planned",
            "agent_skill_brief": self.skill_brief(operation, target, title=title, body=body, number=number, head=head, base=base),
        }
        if execute:
            envelope["result"] = self._execute_operation(envelope)
            envelope["status"] = "executed"
        return envelope

    def skill_brief(self, operation: str, target: str, title: str = "", body: str = "", number: int | None = None, head: str = "", base: str = "") -> str:
        return "\n".join(
            [
                "# GitHub Channel Operation Brief",
                "",
                f"- operation: `{operation}`",
                f"- target: `{target}`",
                f"- number: `{number or ''}`",
                f"- title: `{title}`",
                f"- head: `{head}`",
                f"- base: `{base}`",
                "",
                "Use the repository GitHub skills and repo-local GitHub auth only. Record the result as a channel artifact and mailbox message.",
                "",
                "## Body",
                "",
                body,
                "",
            ]
        )

    def _execute_operation(self, envelope: dict[str, Any]) -> dict[str, Any]:
        self.verify_auth()
        op = envelope["operation"]
        if op == "create_issue":
            return self._gh_json("issue", "create", "--title", envelope["title"], "--body", envelope["body"], "--json", "number,url")
        if op == "comment_issue":
            return self._gh_json("issue", "comment", str(envelope["number"]), "--body", envelope["body"], "--json", "url")
        if op == "close_issue":
            return self._gh_json("issue", "close", str(envelope["number"]), "--json", "number,state")
        if op == "create_pr":
            return self._gh_json("pr", "create", "--title", envelope["title"], "--body", envelope["body"], "--head", envelope["head"], "--base", envelope["base"] or "main", "--json", "number,url")
        if op == "comment_pr":
            return self._gh_json("pr", "comment", str(envelope["number"]), "--body", envelope["body"], "--json", "url")
        if op == "close_pr":
            return self._gh_json("pr", "close", str(envelope["number"]), "--json", "number,state")
        raise ValueError(f"unknown GitHub operation {op!r}")

    def verify_auth(self) -> None:
        if self.auth_dir is None:
            self.auth_dir = self._detect_auth_dir()
        env = os.environ.copy()
        env["GH_CONFIG_DIR"] = str(self.auth_dir)
        subprocess.run(
            ["gh", "auth", "status"],
            cwd=self.repo_root,
            env=env,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def write_comment_envelope(self, target_root: str | Path, envelope: dict[str, Any]) -> Path:
        filename = _safe_filename(f"{envelope.get('channel', 'github')}-{envelope.get('external_comment_id', 'comment')}.json")
        path = inbox_dir(target_root) / filename
        write_json(path, envelope)
        return path

    def _detect_auth_dir(self) -> Path:
        if not shutil.which("gh"):
            raise RuntimeError("GitHub CLI is not installed. Install gh, then run:\n" + SETUP_SCRIPT)
        found = self._find_auth_dir()
        if found is not None:
            return found
        raise RuntimeError("No repo-local gh auth found in .gh/ or tmp/gh/. Run:\n" + SETUP_SCRIPT)

    def _find_auth_dir(self) -> Path | None:
        for rel in [".gh", "tmp/gh"]:
            candidate = self.repo_root / rel
            if (candidate / "hosts.yml").exists():
                return candidate
        return None

    def _gh_json(self, *args: str) -> dict[str, Any]:
        env = os.environ.copy()
        env["GH_CONFIG_DIR"] = str(self.auth_dir)
        proc = subprocess.run(
            ["gh", *args],
            cwd=self.repo_root,
            env=env,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        import json

        return json.loads(proc.stdout)


def github_comment_envelope(
    channel: str,
    comment_id: str,
    thread_id: str,
    author: str,
    body: str,
    target_refs: list[str],
) -> dict[str, Any]:
    return {
        "channel": channel,
        "external_comment_id": comment_id,
        "external_thread_id": thread_id,
        "author": author,
        "body": body,
        "target_refs": target_refs,
    }


def ensure_github_process(root: str | Path, goal_id: str, run_id: str, process_id: str = "github") -> None:
    if process_metadata_path(root, goal_id, run_id, process_id).exists():
        return
    create_process(root, goal_id, run_id, process_id, role="channel", process_kind="virtual", extra={"adapter": {"type": "github"}})


def record_github_operation(
    root: str | Path,
    goal_id: str,
    run_id: str,
    operation: str,
    target: str,
    title: str = "",
    body: str = "",
    number: int | None = None,
    head: str = "",
    base: str = "",
    process_id: str = "github",
    target_process_id: str = "primary",
    execute: bool = False,
) -> dict[str, Any]:
    ensure_github_process(root, goal_id, run_id, process_id)
    adapter = GitHubAdapter(root)
    envelope = adapter.operation_envelope(operation, target, title=title, body=body, number=number, head=head, base=base, execute=execute)
    message = send_message(
        root,
        goal_id,
        run_id,
        process_id,
        target_process_id,
        f"github_{operation}",
        body or title or operation,
        artifact_refs=[],
        requires_ack=False,
    )
    return {"operation": envelope, "message": message}


def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value)
