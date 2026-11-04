"""Story resource: n8n Instagram node -> Story / Publish (tek operasyon).

n8n'deki alanlarin hepsi kabul edilir (parity); ek olarak n8n'de olmayan
image_url ile gorsel story de yayinlanabilir (video_url ile birlikte
verilemez). Graph API story container'i sadece video_url/image_url,
media_type=STORIES ve user_tags destekler. Digerleri verilirse uyari loglanir ve gonderilmez.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Iterable, Optional

from ..client import GraphClient
from ..publisher import publish_media
from .image import TRIAL_STRATEGIES, build_user_tags

log = logging.getLogger(__name__)

STORY_TIMEOUT = 900


def build_story_params(
    video_url: str = "",
    caption: str = "",
    *,
    image_url: str = "",
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
    if bool(video_url) == bool(image_url):
        raise ValueError("video_url veya image_url'den tam olarak biri verilmeli")
    if trial_graduation_strategy and trial_graduation_strategy not in TRIAL_STRATEGIES:
        raise ValueError(
            f"trial_graduation_strategy su degerlerden biri olmali: {sorted(TRIAL_STRATEGIES)}"
        )

    params: dict[str, Any] = {"media_type": "STORIES"}
    if video_url:
        params["video_url"] = video_url
    else:
        params["image_url"] = image_url

    # Story'de user tag icin konum gonderilmez, sadece username.
    ut = [{"username": t["username"]} for t in build_user_tags(user_tags)]
    if ut:
        params["user_tags"] = json.dumps(ut)

    ignored = [
        name
        for name, value in (
            ("caption", caption),
            ("alt_text", alt_text),
            ("audio_name", audio_name),
            ("collaborators", collaborators),
            ("cover_url", cover_url),
            ("location_id", location_id),
            ("product_tags", list(product_tags or [])),
            ("thumbnail_offset", thumbnail_offset),
            ("trial_graduation_strategy", trial_graduation_strategy),
        )
        if value
    ]
    if share_to_feed is False:  # n8n varsayilani True; sadece degistirildiyse uyar
        ignored.append("share_to_feed")
    if ignored:
        log.warning("Story container'inda desteklenmiyor, atlandi: %s", ", ".join(ignored))

    return params


def publish_story(
    client: GraphClient,
    video_url: str = "",
    caption: str = "",
    *,
    image_url: str = "",
    timeout: int = STORY_TIMEOUT,
    interval: int = 5,
    **fields: Any,
) -> dict[str, Any]:
    """Story / Publish: container olustur -> isleme bitene kadar bekle -> yayinla.

    Video story: publish_story(client, "https://.../v.mp4")
    Gorsel story: publish_story(client, image_url="https://.../f.jpg")
    """
    params = build_story_params(video_url, caption, image_url=image_url, **fields)
    return publish_media(client, timeout=timeout, interval=interval, **params)