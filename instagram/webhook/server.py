"""Thin stdlib HTTP server for Meta Instagram webhooks."""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Iterable, Optional
from urllib.parse import parse_qs, urlparse

from .handlers import parse_events, verify_challenge, verify_signature

EventCallback = Callable[[dict], None]


def make_handler(
    *,
    verify_token: str,
    app_secret: str,
    on_event: Optional[EventCallback] = None,
    include: Optional[Iterable[str]] = None,
    path: str = "/webhook",
):
    """Build a BaseHTTPRequestHandler subclass wired to the given credentials."""

    include_list = list(include) if include is not None else None

    class WebhookHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:  # quieter in tests
            return

        def _path_ok(self) -> bool:
            return urlparse(self.path).path.rstrip("/") == path.rstrip("/")

        def do_GET(self) -> None:
            if not self._path_ok():
                self.send_error(404)
                return
            query = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
            try:
                challenge = verify_challenge(query, verify_token)
            except ValueError:
                self.send_error(403, "Verification failed")
                return
            body = challenge.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            if not self._path_ok():
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            sig = self.headers.get("X-Hub-Signature-256")
            if not verify_signature(raw, sig, app_secret):
                self.send_error(403, "Invalid signature")
                return
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
            except (UnicodeDecodeError, json.JSONDecodeError):
                self.send_error(400, "Invalid JSON")
                return
            for event in parse_events(payload, include=include_list):
                if on_event is not None:
                    on_event(event)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")

    return WebhookHandler


def serve_forever(
    host: str = "0.0.0.0",
    port: int = 8080,
    *,
    verify_token: Optional[str] = None,
    app_secret: Optional[str] = None,
    on_event: Optional[EventCallback] = None,
    include: Optional[Iterable[str]] = None,
    path: str = "/webhook",
) -> None:
    """Block serving webhooks. Credentials default from env."""
    verify_token = verify_token or os.getenv("IG_WEBHOOK_VERIFY_TOKEN", "").strip()
    app_secret = app_secret or os.getenv("FB_APP_SECRET", "").strip()
    if not verify_token or not app_secret:
        raise ValueError("IG_WEBHOOK_VERIFY_TOKEN and FB_APP_SECRET are required")

    handler = make_handler(
        verify_token=verify_token,
        app_secret=app_secret,
        on_event=on_event,
        include=include,
        path=path,
    )
    httpd = HTTPServer((host, port), handler)
    httpd.serve_forever()
