from typing import Optional

from ..client import GraphClient

DEFAULT_USER_FIELDS = (
    "id,username,name,biography,website,profile_picture_url,"
    "followers_count,follows_count,media_count"
)

DEFAULT_MEDIA_FIELDS = (
    "id,caption,media_type,media_product_type,media_url,thumbnail_url,"
    "permalink,timestamp,like_count,comments_count"
)


def get(client: GraphClient, fields: str = DEFAULT_USER_FIELDS) -> dict:
    """Get basic profile information for an Instagram Business or Creator account."""
    return client.get(client.node, fields=fields)


def get_media(
    client: GraphClient,
    fields: str = DEFAULT_MEDIA_FIELDS,
    limit: int = 25,
    after: Optional[str] = None,
) -> dict:
    """List media objects owned by an Instagram Business or Creator account.

    Pass the `after` cursor from `paging.cursors.after` to fetch the next page.
    """
    return client.get(
        f"{client.node}/media",
        fields=fields,
        limit=limit,
        after=after,
    )