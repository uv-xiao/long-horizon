from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .comments import inbox_dir
from .io import write_json


SETUP_SCRIPT = """mkdir -p tmp/gh
export GH_CONFIG_DIR="$PWD/tmp/gh"
gh auth login --hostname github.com --git-protocol https --web
gh auth status
"""


class GitHubAdapter:
    def __init__(self, repo_root: str | Path):
        self.repo_root = Path(repo_root).resolve()
        self.auth_dir = self._detect_auth_dir()

    def repo_info(self) -> dict[str, Any]:
        self.verify_auth()
        return self._gh_json("repo", "view", "--json", "nameWithOwner,url")

    def verify_auth(self) -> None:
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
        for rel in [".gh", "tmp/gh"]:
            candidate = self.repo_root / rel
            if (candidate / "hosts.yml").exists():
                return candidate
        raise RuntimeError("No repo-local gh auth found in .gh/ or tmp/gh/. Run:\n" + SETUP_SCRIPT)

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


def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value)
