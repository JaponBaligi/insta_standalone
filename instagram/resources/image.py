from __future__ import annotations

import json
import logging
from typing import Any, Iterable, Optional

from ..client import GraphClient
from ..publisher import publish_media

log = logging.getLogger(__name__)

CAPTION_MAX = 2200
TRIAL_STRATEGIES = {"MANUAL", "SS_PERFORMANCE"}

REEL_ONLY = ("audio_name", "cover_url", "share_to_feed", "thumb_offset", "trial_params")

def _csv_or_list(value: Any) -> list[str]:
    '''Convert a CSV string or iterable into a list of stripped strings, ignoring empty values.'''
    if value is None or value == "":
        return []
    items = value.split(",") if isinstance(value, str) else list(value)
    return [str(i).strip().lstrip("@") for i in items if str(i).strip()]


def _check_pos(name: str, value: float) -> float:
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} 0.0 ile 1.0 arasinda olmali, gelen: {value}")
    return value


def build_user_tags(user_tags: Optional[Iterable[dict]]) -> list[dict]:
    """[{'username': 'x', 'x': 0.5, 'y': 0.5}, ...] -> API format."""
    out = []
    for tag in user_tags or []:
        username = str(tag.get("username", "")).strip().lstrip("@")
        if not username:
            raise ValueError("user_tags: username bos olamaz")
        out.append({
            "username": username,
            "x": _check_pos("user_tags.x", tag.get("x", 0.5)),
            "y": _check_pos("user_tags.y", tag.get("y", 0.5)),
        })
    return out


def build_product_tags(product_tags: Optional[Iterable[dict]]) -> list[dict]:
    """[{'product_id': '123', 'x': 0.5, 'y': 0.5}, ...] -> API format."""
    out = []
    for tag in product_tags or []:
        product_id = str(tag.get("product_id", "")).strip()
        if not product_id:
            raise ValueError("product_tags: product_id cannot be empty")
        out.append({
            "product_id": product_id,
            "x": _check_pos("product_tags.x", tag.get("x", 0.5)),
            "y": _check_pos("product_tags.y", tag.get("y", 0.5)),
        })
    return out


def build_image_params(
    image_url: str,
    caption: str = "",
    *,
    alt_text: str = "",
    collaborators: Any = None,
    location_id: str = "",
    user_tags: Optional[Iterable[dict]] = None,
    product_tags: Optional[Iterable[dict]] = None,
    audio_name: str = "",
    cover_url: str = "",
    share_to_feed: Optional[bool] = None,
    thumbnail_offset: Optional[float] = None,
    trial_graduation_strategy: str = "",
    is_carousel_item: bool = False,
) -> dict[str, Any]:
    if not image_url:
        raise ValueError("image_url cannot be empty")
    if len(caption or "") > CAPTION_MAX:
        raise ValueError(f"caption cannot exceed {CAPTION_MAX} characters")

    params: dict[str, Any] = {"image_url": image_url}

    if is_carousel_item:
        params["is_carousel_item"] = "true"
    elif caption:
        params["caption"] = caption

    if alt_text:
        params["alt_text"] = alt_text
    if location_id:
        params["location_id"] = str(location_id)

    collabs = _csv_or_list(collaborators)
    if collabs:
        params["collaborators"] = json.dumps(collabs)

    ut = build_user_tags(user_tags)
    if ut:
        params["user_tags"] = json.dumps(ut)

    pt = build_product_tags(product_tags)
    if pt:
        params["product_tags"] = json.dumps(pt)

    ignored = []
    if audio_name:
        ignored.append("audio_name")
    if cover_url:
        ignored.append("cover_url")
    if thumbnail_offset:
        ignored.append("thumbnail_offset")
    if trial_graduation_strategy:
        if trial_graduation_strategy not in TRIAL_STRATEGIES:
            raise ValueError(f"trial_graduation_strategy su degerlerden biri olmali: {sorted(TRIAL_STRATEGIES)}")
        ignored.append("trial_graduation_strategy")
    if share_to_feed is False:
        ignored.append("share_to_feed")
    if ignored:
        log.warning("Invalid fields for image container (ignored): %s", ", ".join(ignored))

    return params


def build_reel_extras(
    *,
    audio_name: str = "",
    cover_url: str = "",
    share_to_feed: Optional[bool] = None,
    thumbnail_offset: Optional[float] = None,
    trial_graduation_strategy: str = "",
) -> dict[str, Any]:
    extras: dict[str, Any] = {}
    if audio_name:
        extras["audio_name"] = audio_name
    if cover_url:
        extras["cover_url"] = cover_url
    if share_to_feed is not None:
        extras["share_to_feed"] = "true" if share_to_feed else "false"
    if thumbnail_offset:
        extras["thumb_offset"] = int(float(thumbnail_offset) * 1000)
    if trial_graduation_strategy:
        if trial_graduation_strategy not in TRIAL_STRATEGIES:
            raise ValueError(f"trial_graduation_strategy must be one of: {sorted(TRIAL_STRATEGIES)}")
        extras["trial_params"] = json.dumps({"graduation_strategy": trial_graduation_strategy})
    return extras


def publish_image(
    client: GraphClient,
    image_url: str,
    caption: str = "",
    *,
    timeout: int = 300,
    interval: int = 5,
    **fields: Any,
) -> dict[str, Any]:
    params = build_image_params(image_url, caption, **fields)
    return publish_media(client, timeout=timeout, interval=interval, **params)