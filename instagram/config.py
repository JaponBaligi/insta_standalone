import os
from dataclasses import dataclass
from .exceptions import ConfigError

from dotenv import load_dotenv

load_dotenv()

DEFAULT_API_VERSION = "v25.0"


@dataclass(frozen=True)
class Config:
    access_token: str
    node: str
    api_version: str
    app_id: str
    app_secret: str

    @property
    def base_url(self) -> str:
        return f"https://graph.facebook.com/{self.api_version}"


def load_config() -> Config:
    token = os.getenv("IG_ACCESS_TOKEN", "").strip()
    if not token:
        raise ConfigError("IG_ACCESS_TOKEN environment variable is not set.")

    node = os.getenv("IG_NODE", "").strip()
    if not node:
        raise ConfigError(
            "IG_NODE environment variable is not set. "
            "Set it to your Instagram account ID."
        )
    if node.lower() == "me":
        raise ConfigError(
            "IG_NODE cannot be 'me': with a Facebook-login token 'me' is the "
            "Facebook user, not the Instagram account. Set it to your Instagram "
            "account ID (see resources/page.py: get_instagram_account)."
        )

    return Config(
        access_token=token,
        node=node,
        api_version=os.getenv("IG_GRAPH_API_VERSION", DEFAULT_API_VERSION).strip()
        or DEFAULT_API_VERSION,
        app_id=os.getenv("FB_APP_ID", "").strip(),
        app_secret=os.getenv("FB_APP_SECRET", "").strip(),
    )