"""Comment resource: list, moderate, create, and reply."""
from __future__ import annotations

from typing import Any, Iterator, Optional

from ..client import GraphClient

DEFAULT_FIELDS = (
    "id,text,timestamp,username,like_count,hidden,parent_id,"
    "replies{id,text,timestamp,username,like_count,hidden}"
)


def _require(name: str, value: str) -> str:
    value = str(value or "").strip()
    if not value:
        raise ValueError(f"{name} zorunlu")
    return value


def list_comments(
    client: GraphClient,
    media_id: str,
    *,
    fields: str = DEFAULT_FIELDS,
    limit: Optional[int] = None,
    after: Optional[str] = None,
) -> dict[str, Any]:
    """Tek sayfa yorum dondurur (Graph API cevabi: data + paging)."""
    media_id = _require("media_id", media_id)
    return client.get(f"{media_id}/comments", fields=fields, limit=limit, after=after)


def iter_comments(
    client: GraphClient,
    media_id: str,
    *,
    fields: str = DEFAULT_FIELDS,
    page_size: int = 50,
    max_items: Optional[int] = None,
) -> Iterator[dict[str, Any]]:
    """Tum sayfalari gezerek yorumlari tek tek verir."""
    after: Optional[str] = None
    count = 0
    while True:
        page = list_comments(client, media_id, fields=fields, limit=page_size, after=after)
        for comment in page.get("data", []):
            yield comment
            count += 1
            if max_items is not None and count >= max_items:
                return
        paging = page.get("paging", {})
        after = paging.get("cursors", {}).get("after")
        if not after or not paging.get("next"):
            return


def list_all_comments(client: GraphClient, media_id: str, **kwargs: Any) -> list[dict[str, Any]]:
    return list(iter_comments(client, media_id, **kwargs))


def delete_comment(client: GraphClient, comment_id: str) -> dict[str, Any]:
    return client.delete(_require("comment_id", comment_id))


def hide_comment(client: GraphClient, comment_id: str) -> dict[str, Any]:
    return client.post(_require("comment_id", comment_id), hide=True)


def unhide_comment(client: GraphClient, comment_id: str) -> dict[str, Any]:
    return client.post(_require("comment_id", comment_id), hide=False)


def disable_comments(client: GraphClient, media_id: str) -> dict[str, Any]:
    return client.post(_require("media_id", media_id), comment_enabled=False)


def enable_comments(client: GraphClient, media_id: str) -> dict[str, Any]:
    return client.post(_require("media_id", media_id), comment_enabled=True)


def create_comment(client: GraphClient, media_id: str, message: str) -> dict[str, Any]:
    """Public top-level comment on media owned by the authenticated account."""
    media_id = _require("media_id", media_id)
    message = _require("message", message)
    return client.post(f"{media_id}/comments", message=message)


def reply_to_comment(client: GraphClient, comment_id: str, message: str) -> dict[str, Any]:
    """Public reply under an existing comment."""
    comment_id = _require("comment_id", comment_id)
    message = _require("message", message)
    return client.post(f"{comment_id}/replies", message=message)
