"""Bearer token check for the automation HTTP API."""
from __future__ import annotations

import hmac
from typing import Optional


def check_bearer(authorization_header: Optional[str], expected_token: str) -> bool:
    if not expected_token or not authorization_header:
        return False
    header = authorization_header.strip()
    if not header.lower().startswith("bearer "):
        return False
    provided = header[7:].strip()
    return hmac.compare_digest(provided, expected_token)
