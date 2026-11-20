"""Parse and dispatch publish jobs to resource helpers."""
from __future__ import annotations

from typing import Any

from ..client import GraphClient
from ..resources import carousel, image, reel, story

VALID_TYPES = frozenset({"image", "reel", "story", "carousel"})


class JobError(ValueError):
    """Invalid automation job payload."""


def _url(value: Any, field: str) -> str:
    url = str(value or "").strip()
    if not url.startswith(("http://", "https://")):
        raise JobError(f"{field} must be a public http(s) URL")
    return url


def parse_job(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise JobError("job must be a JSON object")
    job_type = str(payload.get("type") or "").strip().lower()
    if job_type not in VALID_TYPES:
        raise JobError(f"type must be one of: {sorted(VALID_TYPES)}")

    caption = str(payload.get("caption") or "")
    job: dict[str, Any] = {"type": job_type, "caption": caption}

    if job_type == "image":
        job["image_url"] = _url(payload.get("image_url"), "image_url")
    elif job_type == "reel":
        job["video_url"] = _url(payload.get("video_url"), "video_url")
    elif job_type == "story":
        image_url = str(payload.get("image_url") or "").strip()
        video_url = str(payload.get("video_url") or "").strip()
        if bool(image_url) == bool(video_url):
            raise JobError("story requires exactly one of image_url or video_url")
        if image_url:
            job["image_url"] = _url(image_url, "image_url")
        else:
            job["video_url"] = _url(video_url, "video_url")
    else:  # carousel
        items = payload.get("items")
        if not isinstance(items, list) or len(items) < 2:
            raise JobError("carousel requires items list with at least 2 entries")
        normalized = []
        for index, item in enumerate(items, start=1):
            if isinstance(item, str):
                normalized.append(_url(item, f"items[{index}]"))
            elif isinstance(item, dict) and item.get("url"):
                entry = {"url": _url(item.get("url"), f"items[{index}].url")}
                if item.get("media_type"):
                    entry["media_type"] = str(item["media_type"]).strip().lower()
                normalized.append(entry)
            else:
                raise JobError(f"items[{index}] must be a URL string or {{url, media_type?}}")
        job["items"] = normalized
    return job


def run_job(client: GraphClient, payload: dict[str, Any]) -> dict[str, Any]:
    job = parse_job(payload)
    job_type = job["type"]
    caption = job.get("caption") or ""

    if job_type == "image":
        result = image.publish_image(client, job["image_url"], caption=caption)
    elif job_type == "reel":
        result = reel.publish_reel(client, job["video_url"], caption=caption)
    elif job_type == "story":
        if job.get("image_url"):
            result = story.publish_story(client, image_url=job["image_url"], caption=caption)
        else:
            result = story.publish_story(client, job["video_url"], caption=caption)
    else:
        result = carousel.publish_carousel(client, job["items"], caption=caption)

    return {"ok": True, "type": job_type, "result": result}
