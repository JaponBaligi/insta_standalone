import os
from dataclasses import dataclass
from .exceptions import ConfigError

from dotenv import load_dotenv

load_dotenv()

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

    return Config(
        access_token=token,
        node=os.getenv("IG_NODE", "me").strip() or "me",
        api_version=os.getenv("IG_GRAPH_API_VERSION", "v22.0").strip(),
        app_id=os.getenv("FB_APP_ID", "").strip(),
        app_secret=os.getenv("FB_APP_SECRET", "").strip(),
    )