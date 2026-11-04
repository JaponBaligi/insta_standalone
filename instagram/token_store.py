import json
import time
from pathlib import Path
from typing import Optional

STORE_PATH = Path(__file__).resolve().parent.parent / "token" / ".token.json"


def load() -> Optional[dict]:
    """Return the stored token data, or None if missing or unreadable."""
    if not STORE_PATH.exists():
        return None
    try:
        return json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def save(token: str, expires_in: Optional[int] = None) -> dict:
    """Persist the token and its expiry timestamp (None if unknown)."""
    now = int(time.time())
    data = {
        "access_token": token,
        "expires_at": now + int(expires_in) if expires_in else None,
        "saved_at": now,
    }
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(json.dumps(data), encoding="utf-8")
    return data


def seconds_left(data: Optional[dict]) -> Optional[int]:
    """Seconds until expiry, or None if there is no expiry information."""
    if not data or not data.get("expires_at"):
        return None
    return data["expires_at"] - int(time.time())