"""Live Graph API feature pass — calls only package public APIs.

Run from repo root:
  python test_content/run_live_features.py

Uploads local media from test_content/ to a temporary public host so Meta can
fetch image_url / video_url (required by Content Publishing).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import sys
import traceback
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from instagram.client import GraphClient
from instagram.resources import (
    auth,
    carousel,
    comment,
    image,
    page,
    reel,
    story,
    user,
)
from instagram.webhook import parse_events, verify_challenge, verify_signature

CONTENT = Path(__file__).resolve().parent
IMAGE = CONTENT / "webpp.png"
VIDEO = CONTENT / "VID-20210406-WA0011.mp4"


def step(title: str) -> None:
    print(f"\n=== {title} ===", flush=True)


def ok(payload) -> None:
    print("OK", _short(payload), flush=True)


def fail(exc: BaseException) -> None:
    print("FAIL", f"{type(exc).__name__}: {exc}", flush=True)


def _redact(obj):
    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            if "token" in str(key).lower() and isinstance(value, str) and value:
                out[key] = value[:6] + "…<redacted>"
            else:
                out[key] = _redact(value)
        return out
    if isinstance(obj, list):
        return [_redact(v) for v in obj]
    return obj


def _short(payload, limit: int = 400) -> str:
    try:
        text = json.dumps(_redact(payload), ensure_ascii=False, default=str)
    except TypeError:
        text = str(payload)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def upload_public(path: Path) -> str:
    with path.open("rb") as handle:
        response = requests.post(
            "https://litterbox.catbox.moe/resources/internals/api.php",
            data={"reqtype": "fileupload", "time": "1h"},
            files={"fileToUpload": (path.name, handle)},
            timeout=180,
        )
    response.raise_for_status()
    url = response.text.strip()
    if not url.startswith("http"):
        raise RuntimeError(f"upload failed: {url}")
    return url


def main() -> int:
    client = GraphClient()
    published_media_id = None
    comment_id = None

    step("auth.get_me")
    try:
        ok(auth.get_me(client))
    except Exception as exc:
        fail(exc)

    step("page.list_pages")
    try:
        pages = page.list_pages(client)
        ok(pages)
        for item in pages.get("data") or []:
            step(f"page.get_instagram_account({item.get('id')})")
            try:
                ok(page.get_instagram_account(client, item["id"]))
            except Exception as exc:
                fail(exc)
    except Exception as exc:
        fail(exc)

    step("user.get")
    try:
        ok(user.get(client))
    except Exception as exc:
        fail(exc)

    step("user.get_media")
    try:
        ok(user.get_media(client, limit=5))
    except Exception as exc:
        fail(exc)

    step("upload local media for public URLs")
    try:
        image_url = upload_public(IMAGE)
        video_url = upload_public(VIDEO)
        print("image_url", image_url, flush=True)
        print("video_url", video_url, flush=True)
    except Exception as exc:
        fail(exc)
        return 1

    step("image.publish_image")
    try:
        result = image.publish_image(
            client, image_url, caption="live: image.publish_image"
        )
        published_media_id = result.get("id")
        ok(result)
    except Exception as exc:
        fail(exc)

    step("story.publish_story (image)")
    try:
        ok(story.publish_story(client, image_url=image_url))
    except Exception as exc:
        fail(exc)

    step("reel.publish_reel")
    try:
        ok(reel.publish_reel(client, video_url, caption="live: reel.publish_reel"))
    except Exception as exc:
        fail(exc)

    step("carousel.publish_carousel")
    try:
        ok(
            carousel.publish_carousel(
                client,
                items=[image_url, image_url],
                caption="live: carousel.publish_carousel",
            )
        )
    except Exception as exc:
        fail(exc)

    if published_media_id:
        step("comment.create_comment")
        try:
            created = comment.create_comment(
                client, published_media_id, "live: create_comment"
            )
            comment_id = created.get("id")
            ok(created)
        except Exception as exc:
            fail(exc)

        step("comment.list_comments")
        try:
            ok(comment.list_comments(client, published_media_id))
        except Exception as exc:
            fail(exc)

        if comment_id:
            step("comment.reply_to_comment")
            try:
                ok(comment.reply_to_comment(client, comment_id, "live: reply_to_comment"))
            except Exception as exc:
                fail(exc)

            step("comment.hide_comment / unhide_comment")
            try:
                ok(comment.hide_comment(client, comment_id))
                ok(comment.unhide_comment(client, comment_id))
            except Exception as exc:
                fail(exc)

        step("comment.disable_comments / enable_comments")
        try:
            ok(comment.disable_comments(client, published_media_id))
            ok(comment.enable_comments(client, published_media_id))
        except Exception as exc:
            fail(exc)

    step("webhook helpers (local, no Meta callback)")
    try:
        challenge = verify_challenge(
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "live-verify",
                "hub.challenge": "123",
            },
            verify_token="live-verify",
        )
        body = b'{"object":"instagram","entry":[]}'
        secret = client.config.app_secret or "test"
        sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        signed = verify_signature(body, sig, secret)
        events = parse_events(
            {
                "object": "instagram",
                "entry": [
                    {
                        "id": "1",
                        "time": 1,
                        "changes": [{"field": "comments", "value": {"id": "c"}}],
                    }
                ],
            }
        )
        ok({"challenge": challenge, "signed": signed, "events": events})
    except Exception as exc:
        fail(exc)
        traceback.print_exc()

    step("auth.refresh_access_token")
    try:
        ok(auth.refresh_access_token(client))
    except Exception as exc:
        fail(exc)

    print("\nDone.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
