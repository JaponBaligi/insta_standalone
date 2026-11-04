"""Carousel resource: n8n Instagram node -> Carousel / Publish (tek operasyon).

n8n'deki iki giris modu:
  - Manual Media Items   -> items=[{"media_type": "image", "url": ...}, ...]
  - Use Field From Input -> items=[url, url, ...] + media_type="auto"|"image"|"video"
                            (veya carousel_items_from_field ile bir dict'ten okunur)

Akis: her child icin container -> hazir olana kadar bekle -> parent
(CAROUSEL) container -> bekle -> media_publish.
"""
from __future__ import annotations

import logging
from typing import Any, Iterable, Union
from urllib.parse import urlparse

from ..client import GraphClient
from ..publisher import create_container, publish_container, wait_until_ready
from .image import CAPTION_MAX, build_image_params

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
    """Girdiyi [{'media_type': 'image'|'video', 'url': ...}] listesine cevirir.

    - str eleman: media_type parametresine gore (auto ise uzantidan)
    - dict eleman: 'media_type' (yoksa auto) ve 'url' (veya image_url / video_url)
    """
    if media_type not in MEDIA_TYPES:
        raise ValueError(f"media_type su degerlerden biri olmali: {sorted(MEDIA_TYPES)}")

    out: list[dict[str, str]] = []
    for i, item in enumerate(items, start=1):
        if isinstance(item, str):
            url, kind = item.strip(), media_type
        elif isinstance(item, dict):
            url = str(item.get("url") or item.get("image_url") or item.get("video_url") or "").strip()
            kind = str(item.get("media_type") or media_type).lower()
        else:
            raise ValueError(f"Carousel ogesi {i}: str veya dict olmali")

        if not url:
            raise ValueError(f"Carousel ogesi {i}: url bos")
        if kind not in MEDIA_TYPES:
            raise ValueError(f"Carousel ogesi {i}: gecersiz media_type '{kind}'")
        if kind == "auto":
            kind = detect_media_type(url)
        out.append({"media_type": kind, "url": url})

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


def build_child_params(item: dict[str, str]) -> dict[str, Any]:
    if item["media_type"] == "image":
        return build_image_params(item["url"], is_carousel_item=True)
    return {"media_type": "VIDEO", "video_url": item["url"], "is_carousel_item": True}


def publish_carousel(
    client: GraphClient,
    items: Iterable[Union[str, dict]],
    caption: str = "",
    *,
    media_type: str = "auto",
    timeout: int = CAROUSEL_TIMEOUT,
    interval: int = 5,
) -> dict[str, Any]:
    """Carousel / Publish.

    Manual:  publish_carousel(client, [{"media_type": "image", "url": "..."},
                                       {"media_type": "video", "url": "..."}], "caption")
    Dizi:    publish_carousel(client, ["a.jpg", "b.mp4"], "caption", media_type="auto")
    """
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
        media_type="CAROUSEL",
        children=",".join(child_ids),
        caption=caption or None,
    )
    wait_until_ready(client, parent_id, timeout=timeout, interval=interval)

    return publish_container(client, parent_id)