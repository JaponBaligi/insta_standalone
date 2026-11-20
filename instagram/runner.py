"""CLI entrypoint for automation serve / one-shot publish.

Examples:
  python -m instagram.runner serve --port 8787
  python -m instagram.runner publish --file job.json
  python -m instagram.runner publish --json '{"type":"image","image_url":"https://…"}'
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .automation import jobs
from .automation.http import serve_forever
from .client import GraphClient
from .exceptions import InstagramError


def _load_job(args: argparse.Namespace) -> dict:
    if args.json and args.file:
        raise SystemExit("use only one of --json or --file")
    if args.json:
        try:
            return json.loads(args.json)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"invalid --json: {exc}") from exc
    if args.file:
        path = Path(args.file)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"cannot read job file: {exc}") from exc
    raise SystemExit("provide --json or --file")


def cmd_serve(args: argparse.Namespace) -> int:
    print(f"automation listening on http://{args.host}:{args.port}", flush=True)
    print("POST /v1/publish  GET /health", flush=True)
    serve_forever(host=args.host, port=args.port)
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    payload = _load_job(args)
    try:
        result = jobs.run_job(GraphClient(), payload)
    except jobs.JobError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), flush=True)
        return 2
    except InstagramError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), flush=True)
        return 3
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="instagram.runner", description="Instagram automation runner")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="HTTP server for Telegram / automation triggers")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8787)
    serve.set_defaults(func=cmd_serve)

    publish = sub.add_parser("publish", help="One-shot publish job")
    publish.add_argument("--json", help="Job JSON string")
    publish.add_argument("--file", help="Path to job JSON file")
    publish.set_defaults(func=cmd_publish)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
