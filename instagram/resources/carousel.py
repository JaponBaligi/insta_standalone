from __future__ import annotations

import json
import logging
from typing import Any, Iterable, Optional, Union
from urllib.parse import urlparse

from ..client import GraphClient
from ..publisher import create_container, publish_container, wait_until_ready
from .image import CAPTION_MAX, _csv_or_list, build_image_params, build_product_tags

log = logging.getLogger(__name__)

MIN_ITEMS = 2
MAX_ITEMS = 10
CAROUSEL_TIMEOUT = 900

MEDIA_TYPES = {"auto", "image", "video"}
VIDEO_EXTENSIONS = {
    ".mp4", ".mov", ".m4v", ".avi", ".wmv", ".webm", ".mkv", ".mpg", ".mpeg", ".3gp",
}


def detect_media_type(url: str) -> str:
    """Uzantidan tahmin et; emin degilse 'image' (n8n'deki gibi)."""
    path = urlparse(url).path.lower()
    return "video" if any(path.endswith(ext) for ext in VIDEO_EXTENSIONS) else "image"


def normalize_items(
    items: Iterable[Union[str, dict]],
    media_type: str = "auto",
) -> list[dict[str, str]]:

    if media_type not in MEDIA_TYPES:
        raise ValueError(f"media_type su degerlerden biri olmali: {sorted(MEDIA_TYPES)}")

    out: list[dict[str, Any]] = []
    for i, item in enumerate(items, start=1):
        user_tags = None
        if isinstance(item, str):
            url, kind = item.strip(), media_type
        elif isinstance(item, dict):
            url = str(item.get("url") or item.get("image_url") or item.get("video_url") or "").strip()
            kind = str(item.get("media_type") or media_type).lower()
            user_tags = item.get("user_tags")
        else:
            raise ValueError(f"Carousel ogesi {i}: str veya dict olmali")

        if not url:
            raise ValueError(f"Carousel ogesi {i}: url bos")
        if kind not in MEDIA_TYPES:
            raise ValueError(f"Carousel ogesi {i}: gecersiz media_type '{kind}'")
        if kind == "auto":
            kind = detect_media_type(url)
        entry: dict[str, Any] = {"media_type": kind, "url": url}
        if user_tags:
            entry["user_tags"] = user_tags
        out.append(entry)

    if not MIN_ITEMS <= len(out) <= MAX_ITEMS:
        raise ValueError(f"Carousel {MIN_ITEMS}-{MAX_ITEMS} oge icermeli, gelen: {len(out)}")
    return out


def carousel_items_from_field(
    data: dict,
    field_name: str,
    media_type: str = "auto",
) -> list[dict[str, str]]:
    """n8n 'Use Field From Input': dict icindeki URL dizisini okur."""
    if not field_name:
        raise ValueError("field_name zorunlu")
    urls = data.get(field_name)
    if not isinstance(urls, (list, tuple)):
        raise ValueError(f"'{field_name}' alani bir liste olmali")
    return normalize_items(urls, media_type)


def build_child_params(item: dict[str, Any]) -> dict[str, Any]:
    if item["media_type"] == "image":
        return build_image_params(
            item["url"], is_carousel_item=True, user_tags=item.get("user_tags")
        )
    if item.get("user_tags"):
        log.warning("Video child'da user_tags desteklenmiyor, atlandi: %s", item["url"])
    return {"media_type": "VIDEO", "video_url": item["url"], "is_carousel_item": True}


def build_parent_params(
    child_ids: list[str],
    caption: str = "",
    *,
    collaborators: Any = None,
    location_id: str = "",
    product_tags: Optional[Iterable[dict]] = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "media_type": "CAROUSEL",
        "children": ",".join(child_ids),
    }
    if caption:
        params["caption"] = caption
    if location_id:
        params["location_id"] = str(location_id)

    collabs = _csv_or_list(collaborators)
    if collabs:
        params["collaborators"] = json.dumps(collabs)

    pt = build_product_tags(product_tags)
    if pt:
        params["product_tags"] = json.dumps(pt)
    return params


def publish_carousel(
    client: GraphClient,
    items: Iterable[Union[str, dict]],
    caption: str = "",
    *,
    media_type: str = "auto",
    collaborators: Any = None,
    location_id: str = "",
    product_tags: Optional[Iterable[dict]] = None,
    timeout: int = CAROUSEL_TIMEOUT,
    interval: int = 5,
) -> dict[str, Any]:
    if len(caption or "") > CAPTION_MAX:
        raise ValueError(f"caption en fazla {CAPTION_MAX} karakter olabilir")

    normalized = normalize_items(items, media_type)

    child_ids: list[str] = []
    for item in normalized:
        child_id = create_container(client, **build_child_params(item))
        wait_until_ready(client, child_id, timeout=timeout, interval=interval)
        child_ids.append(child_id)

    parent_id = create_container(
        client,
        **build_parent_params(
            child_ids,
            caption,
            collaborators=collaborators,
            location_id=location_id,
            product_tags=product_tags,
        ),
    )
    wait_until_ready(client, parent_id, timeout=timeout, interval=interval)

    return publish_container(client, parent_id)