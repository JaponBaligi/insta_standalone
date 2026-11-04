from typing import Optional

from ..client import GraphClient
from ..exceptions import ConfigError


def get_me(client: GraphClient, fields: str = "id,name") -> dict:
    """Call /me with the configured token."""
    return client.get("me", fields=fields)


def exchange_access_token(
    client: GraphClient,
    short_lived_token: str,
    app_secret: Optional[str] = None,
) -> dict:
    """Exchange a short-lived token for a long-lived one (about 60 days)."""
    app_id = client.config.app_id
    app_secret = app_secret or client.config.app_secret

    if not app_id or not app_secret:
        raise ConfigError("FB_APP_ID and FB_APP_SECRET must be set to exchange a token.")

    return client.get(
        "oauth/access_token",
        grant_type="fb_exchange_token",
        client_id=app_id,
        client_secret=app_secret,
        fb_exchange_token=short_lived_token,
    )


def refresh_access_token(client: GraphClient) -> dict:
    """Refresh the configured long-lived token.

    Facebook-login tokens have no dedicated refresh endpoint, so this
    exchanges the current token again to get a new 60-day token.
    """
    return exchange_access_token(client, client.config.access_token)