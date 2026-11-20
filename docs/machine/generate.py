"""Regenerate docs/machine JSON artifacts from docs/*.md (excludes superpowers/machine)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent

PURPOSE = {
    "USAGE.md": "Human setup and end-to-end usage guide for the Instagram Graph client and automation trigger.",
    "nodes/README.md": "Index of per-module node documentation under docs/nodes.",
    "nodes/automation.md": "Inbound automation HTTP/CLI trigger (Telegram-style job JSON + Bearer auth).",
    "nodes/client.md": "GraphClient HTTP + token auto-refresh.",
    "nodes/config.md": ".env Config loading and IG_NODE rules.",
    "nodes/token_store.md": "Persistent token/.token.json store.",
    "nodes/publisher.md": "Shared media container create/wait/publish pipeline.",
    "nodes/exceptions.md": "Exception taxonomy for the package.",
    "nodes/resources/auth.md": "Auth helpers: me, exchange, refresh.",
    "nodes/resources/page.md": "Facebook Page listing and Instagram business account discovery.",
    "nodes/resources/user.md": "IG user profile and owned media listing.",
    "nodes/resources/image.md": "Feed image publish.",
    "nodes/resources/reel.md": "Reels publish.",
    "nodes/resources/story.md": "Stories publish.",
    "nodes/resources/carousel.md": "Carousel/album publish.",
    "nodes/resources/comment.md": "Comment list/moderate/create/reply.",
    "nodes/webhook/handlers.md": "Meta webhook challenge, HMAC signature, event parse helpers.",
    "nodes/webhook/server.md": "Stdlib Meta Instagram webhook HTTP server.",
}

SOURCE = {
    "nodes/client.md": "instagram/client.py",
    "nodes/config.md": "instagram/config.py",
    "nodes/token_store.md": "instagram/token_store.py",
    "nodes/publisher.md": "instagram/publisher.py",
    "nodes/exceptions.md": "instagram/exceptions.py",
    "nodes/resources/auth.md": "instagram/resources/auth.py",
    "nodes/resources/page.md": "instagram/resources/page.py",
    "nodes/resources/user.md": "instagram/resources/user.py",
    "nodes/resources/image.md": "instagram/resources/image.py",
    "nodes/resources/reel.md": "instagram/resources/reel.py",
    "nodes/resources/story.md": "instagram/resources/story.py",
    "nodes/resources/carousel.md": "instagram/resources/carousel.py",
    "nodes/resources/comment.md": "instagram/resources/comment.py",
    "nodes/webhook/handlers.md": "instagram/webhook/handlers.py",
    "nodes/webhook/server.md": "instagram/webhook/server.py",
    "nodes/automation.md": "instagram/automation/*, instagram/runner.py",
}


def _line_count(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def collect() -> list[dict]:
    documents = []
    for path in sorted(DOCS.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(DOCS).as_posix()
        if rel.startswith("machine/") or rel.startswith("superpowers/"):
            continue
        if path.name == "generate.py":
            continue
        text = path.read_text(encoding="utf-8")
        kind = "guide" if rel == "USAGE.md" else ("index" if rel.endswith("README.md") else "node")
        documents.append(
            {
                "id": rel.replace("/", ".").rsplit(".", 1)[0],
                "path": f"docs/{rel}",
                "relative_to_docs": rel,
                "kind": kind,
                "format": path.suffix.lstrip(".") or "txt",
                "purpose": PURPOSE.get(rel, "Documentation file under docs/."),
                "related_source": SOURCE.get(rel),
                "bytes": path.stat().st_size,
                "line_count": _line_count(text),
                "content": text,
            }
        )
    return documents


def main() -> None:
    documents = collect()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    catalog = {
        "schema_version": 1,
        "generated_at": generated_at,
        "project": "insta_standalone",
        "description": (
            "Machine-readable mirror of human docs under docs/ "
            "(excludes docs/superpowers and docs/machine). "
            "Includes full file contents, purpose, and related source paths."
        ),
        "exclusions": ["docs/superpowers/**", "docs/machine/**"],
        "document_count": len(documents),
        "documents": documents,
    }
    (OUT / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    index = {
        "schema_version": 1,
        "generated_at": generated_at,
        "catalog": "docs/machine/catalog.json",
        "documents": [
            {
                "id": d["id"],
                "path": d["path"],
                "kind": d["kind"],
                "purpose": d["purpose"],
                "related_source": d["related_source"],
                "line_count": d["line_count"],
            }
            for d in documents
        ],
    }
    (OUT / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (OUT / "documents.jsonl").open("w", encoding="utf-8") as fh:
        for d in documents:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")
    schema = {
        "schema_version": 1,
        "files": {
            "index.json": "Lightweight list of all docs without content bodies.",
            "catalog.json": "Full catalog including content for every docs file.",
            "documents.jsonl": "Same documents as catalog, one JSON object per line.",
            "schema.json": "This schema description.",
            "generate.py": "Regenerator script.",
            "README.md": "Human note for this folder.",
        },
        "document_fields": {
            "id": "Stable id derived from path under docs/.",
            "path": "Repo-relative path starting with docs/.",
            "relative_to_docs": "Path relative to docs/.",
            "kind": "guide | index | node",
            "format": "File extension without dot (usually md).",
            "purpose": "Short machine-oriented purpose string.",
            "related_source": "Primary instagram/* source path(s), or null.",
            "bytes": "File size in bytes.",
            "line_count": "Approximate line count.",
            "content": "Full UTF-8 text of the document (catalog.json / documents.jsonl only).",
        },
    }
    (OUT / "schema.json").write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(documents)} documents -> {OUT}")


if __name__ == "__main__":
    main()
