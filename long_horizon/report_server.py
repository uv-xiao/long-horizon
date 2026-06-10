from __future__ import annotations

import json
import mimetypes
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .comments import import_comments, inbox_dir
from .io import read_json, write_json
from .paths import reports_dir
from .report import generate_report


class ReportServer:
    def __init__(self, root: str | Path, goal_id: str, run_id: str, host: str = "127.0.0.1", port: int = 0):
        self.root = Path(root).resolve()
        self.goal_id = goal_id
        self.run_id = run_id
        self.host = host
        self.port = port
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        if not self._httpd:
            raise RuntimeError("report server is not running")
        host, port = self._httpd.server_address
        return f"http://{host}:{port}"

    def start(self) -> "ReportServer":
        handler = _handler(self.root, self.goal_id, self.run_id)
        self._httpd = ThreadingHTTPServer((self.host, self.port), handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, name="long-horizon-report-server", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
        if self._thread:
            self._thread.join(timeout=5)
        self._httpd = None
        self._thread = None

    def serve_forever(self) -> None:
        handler = _handler(self.root, self.goal_id, self.run_id)
        self._httpd = ThreadingHTTPServer((self.host, self.port), handler)
        host, port = self._httpd.server_address
        print(f"Serving long-horizon report at http://{host}:{port}", flush=True)
        self._httpd.serve_forever()

    def __enter__(self) -> "ReportServer":
        return self.start()

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.stop()


def _handler(root: Path, goal_id: str, run_id: str):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path in {"/", "/progress.html"}:
                generate_report(root, goal_id, run_id)
                self._send_file(reports_dir(root, goal_id, run_id) / "progress.html")
                return
            if self.path == "/report-data.json":
                generate_report(root, goal_id, run_id)
                self._send_json(read_json(reports_dir(root, goal_id, run_id) / "report-data.json"))
                return
            self.send_error(404, "not found")

        def do_POST(self) -> None:
            if self.path != "/comments":
                self.send_error(404, "not found")
                return
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            try:
                envelope = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError as exc:
                self.send_error(400, f"invalid JSON: {exc}")
                return
            try:
                path = _write_inbox(root, envelope)
                imported = import_comments(root, goal_id, run_id)
                generate_report(root, goal_id, run_id)
            except ValueError as exc:
                self.send_error(400, str(exc))
                return
            self._send_json({"accepted": True, "inbox_path": str(path), "imported_count": len(imported)})

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send_file(self, path: Path) -> None:
            if not path.exists():
                self.send_error(404, "not found")
                return
            content_type, _ = mimetypes.guess_type(path.name)
            self.send_response(200)
            self.send_header("Content-Type", content_type or "text/plain")
            self.end_headers()
            self.wfile.write(path.read_bytes())

        def _send_json(self, payload: Any) -> None:
            body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def _write_inbox(root: Path, envelope: dict[str, Any]) -> Path:
    channel = envelope.get("channel")
    comment_id = envelope.get("external_comment_id")
    if not channel or not comment_id:
        raise ValueError("comment envelope requires channel and external_comment_id")
    filename = _safe_filename(f"{channel}-{comment_id}.json")
    path = inbox_dir(root) / filename
    write_json(path, envelope)
    return path


def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value)
