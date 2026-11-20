"""Stdlib HTTP server for inbound automation publish jobs."""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Optional

from ..client import GraphClient
from ..exceptions import InstagramError
from .auth import check_bearer
from . import jobs


ClientFactory = Callable[[], GraphClient]


def make_handler(
    *,
    automation_token: str,
    client_factory: Optional[ClientFactory] = None,
):
    factory = client_factory or GraphClient

    class AutomationHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            return

        def _send_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path.rstrip("/") == "/health":
                self._send_json(200, {"ok": True})
                return
            self._send_json(404, {"ok": False, "error": "not found"})

        def do_POST(self) -> None:
            if self.path.rstrip("/") != "/v1/publish":
                self._send_json(404, {"ok": False, "error": "not found"})
                return
            if not check_bearer(self.headers.get("Authorization"), automation_token):
                self._send_json(401, {"ok": False, "error": "unauthorized"})
                return
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_json(400, {"ok": False, "error": "invalid JSON"})
                return
            try:
                result = jobs.run_job(factory(), payload)
            except jobs.JobError as exc:
                self._send_json(400, {"ok": False, "error": str(exc)})
                return
            except InstagramError as exc:
                self._send_json(502, {"ok": False, "error": str(exc)})
                return
            except Exception as exc:
                self._send_json(500, {"ok": False, "error": str(exc)})
                return
            self._send_json(200, result)

    return AutomationHandler


def serve_forever(
    host: str = "0.0.0.0",
    port: int = 8787,
    *,
    automation_token: Optional[str] = None,
) -> None:
    token = (automation_token or os.getenv("AUTOMATION_TOKEN", "")).strip()
    if not token:
        raise ValueError("AUTOMATION_TOKEN is required")
    handler = make_handler(automation_token=token)
    HTTPServer((host, port), handler).serve_forever()
