"""Reel resource: n8n Instagram node -> Reel / Publish (tek operasyon).

Alan isimleri n8n arayuzuyle ayni. Ortak donusumler image.py'den gelir.
"""
from __future__ import annotations

import logging
from typing import Any, Iterable, Optional

from ..client import GraphClient
from ..publisher import publish_media
from .image import (
    CAPTION_MAX,
    build_product_tags,
    build_reel_extras,
    build_user_tags,
    _csv_or_list,
)

import json

log = logging.getLogger(__name__)

# Video isleme gorselden uzun surer.
REEL_TIMEOUT = 900


def build_reel_params(
    video_url: str,
    caption: str = "",
    *,
    alt_text: str = "",
    audio_name: str = "",
    collaborators: Any = None,
    cover_url: str = "",
    location_id: str = "",
    product_tags: Optional[Iterable[dict]] = None,
    share_to_feed: Optional[bool] = True,
    thumbnail_offset: Optional[float] = None,
    trial_graduation_strategy: str = "",
    user_tags: Optional[Iterable[dict]] = None,
) -> dict[str, Any]:
    if not video_url:
        raise ValueError("video_url zorunlu")
    if len(caption or "") > CAPTION_MAX:
        raise ValueError(f"caption en fazla {CAPTION_MAX} karakter olabilir")

    params: dict[str, Any] = {"media_type": "REELS", "video_url": video_url}

    if caption:
        params["caption"] = caption
    if location_id:
        params["location_id"] = str(location_id)

    collabs = _csv_or_list(collaborators)
    if collabs:
        params["collaborators"] = json.dumps(collabs)

    # Reel'de user tag icin konum (x, y) gonderilmez, sadece username.
    ut = [{"username": t["username"]} for t in build_user_tags(user_tags)]
    if ut:
        params["user_tags"] = json.dumps(ut)

    pt = build_product_tags(product_tags)
    if pt:
        params["product_tags"] = json.dumps(pt)

    # audio_name, cover_url, share_to_feed, thumb_offset, trial_params
    params.update(
        build_reel_extras(
            audio_name=audio_name,
            cover_url=cover_url,
            share_to_feed=share_to_feed,
            thumbnail_offset=thumbnail_offset,
            trial_graduation_strategy=trial_graduation_strategy,
        )
    )

    if cover_url and thumbnail_offset:
        log.warning("cover_url ve thumbnail_offset birlikte verildi; Instagram cover_url'i kullanir.")

    # alt_text API'de gorsellere ozel; n8n'de gorunur oldugu icin kabul edilir ama gonderilmez.
    if alt_text:
        log.warning("alt_text reel container'inda desteklenmiyor, atlandi.")

    return params


def publish_reel(
    client: GraphClient,
    video_url: str,
    caption: str = "",
    *,
    timeout: int = REEL_TIMEOUT,
    interval: int = 5,
    **fields: Any,
) -> dict[str, Any]:
    """Reel / Publish: container olustur -> isleme bitene kadar bekle -> yayinla."""
    params = build_reel_params(video_url, caption, **fields)
    return publish_media(client, timeout=timeout, interval=interval, **params)