"""IG Hashtag resource: n8n Instagram node -> IG Hashtag operasyonlari.

Operasyonlar: Search, Get Recent Media, Get Top Media

n8n'deki gibi Get Recent/Top Media dogrudan Hashtag ID alir (Return All ve
Limit ile). Istersen ID yerine hashtag_name da verilebilir, o zaman once
arama yapilir.

Meta kisitlari: bir hesap 7 gunluk pencerede en fazla 30 benzersiz hashtag
sorgulayabilir; recent media son 24 saati kapsar; sayfa basina en fazla 50.
"""
from __future__ import annotations

from typing import Any, Iterator, Optional

from ..client import GraphClient

DEFAULT_MEDIA_FIELDS = (
    "id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count,children"
)
MAX_PAGE_SIZE = 50
DEFAULT_MAX_ITEMS = 500  # safety ceiling for return_all


def _clean_name(hashtag_name: str) -> str:
    name = str(hashtag_name or "").strip().lstrip("#")
    if not name:
        raise ValueError("hashtag_name zorunlu")
    if any(ch.isspace() for ch in name):
        raise ValueError("hashtag_name bosluk icermemeli")
    return name


def _user_id(client: GraphClient) -> str:
    """Hashtag endpoints need the real IG user ID (IG_NODE, validated in config)."""
    return client.node


# --- Search -----------------------------------------------------------------

def search_hashtag(client: GraphClient, hashtag_name: str) -> dict[str, Any]:
    """Hashtag'i isimle arar, ID'sini dondurur: {"data": [{"id": "..."}]}."""
    return client.get(
        "ig_hashtag_search",
        user_id=_user_id(client),
        q=_clean_name(hashtag_name),
    )


def get_hashtag_id(client: GraphClient, hashtag_name: str) -> str:
    data = search_hashtag(client, hashtag_name).get("data", [])
    if not data:
        raise LookupError(f"Hashtag bulunamadi: {hashtag_name}")
    return data[0]["id"]


# --- Get Recent Media / Get Top Media ---------------------------------------

def _iter_media(
    client: GraphClient,
    edge: str,
    hashtag_id: str,
    fields: str,
    page_size: int,
) -> Iterator[dict[str, Any]]:
    after: Optional[str] = None
    while True:
        page = client.get(
            f"{hashtag_id}/{edge}",
            user_id=_user_id(client),
            fields=fields,
            limit=page_size,
            after=after,
        )
        yield from page.get("data", [])
        paging = page.get("paging", {})
        after = paging.get("cursors", {}).get("after")
        if not after or not paging.get("next"):
            return


def _media(
    client: GraphClient,
    edge: str,
    hashtag_id: str,
    hashtag_name: str,
    return_all: bool,
    limit: int,
    fields: str,
    max_items: int,
) -> list[dict[str, Any]]:
    if not hashtag_id:
        hashtag_id = get_hashtag_id(client, hashtag_name)
    if not return_all and limit < 1:
        raise ValueError("limit en az 1 olmali")
    if return_all and max_items < 1:
        raise ValueError("max_items en az 1 olmali")

    cap = max_items if return_all else limit
    page_size = min(cap, MAX_PAGE_SIZE)
    items: list[dict[str, Any]] = []
    for media in _iter_media(client, edge, hashtag_id, fields, page_size):
        items.append(media)
        if len(items) >= cap:
            break
    return items


def get_recent_media(
    client: GraphClient,
    hashtag_id: str = "",
    *,
    hashtag_name: str = "",
    return_all: bool = False,
    limit: int = 50,
    fields: str = DEFAULT_MEDIA_FIELDS,
    max_items: int = DEFAULT_MAX_ITEMS,
) -> list[dict[str, Any]]:
    """Hashtag ile etiketlenen en yeni medyalar (liste dondurur).

    return_all=True iken en fazla max_items sonuc doner."""
    return _media(client, "recent_media", hashtag_id, hashtag_name, return_all, limit, fields, max_items)


def get_top_media(
    client: GraphClient,
    hashtag_id: str = "",
    *,
    hashtag_name: str = "",
    return_all: bool = False,
    limit: int = 50,
    fields: str = DEFAULT_MEDIA_FIELDS,
    max_items: int = DEFAULT_MAX_ITEMS,
) -> list[dict[str, Any]]:
    """Hashtag ile etiketlenen en populer medyalar (liste dondurur).

    return_all=True iken en fazla max_items sonuc doner."""
    return _media(client, "top_media", hashtag_id, hashtag_name, return_all, limit, fields, max_items)