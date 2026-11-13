"""Meta Instagram webhook helpers: challenge, signature, event parse."""
from __future__ import annotations

import hashlib
import hmac
from typing import Any, Iterable, Mapping, Optional


def verify_challenge(query: Mapping[str, str], verify_token: str) -> str:
    """Return hub.challenge when Meta's subscription handshake matches."""
    mode = (query.get("hub.mode") or "").strip()
    token = (query.get("hub.verify_token") or "").strip()
    challenge = query.get("hub.challenge")
    if mode != "subscribe" or token != verify_token or challenge is None or challenge == "":
        raise ValueError("Webhook verification failed")
    return str(challenge)


def verify_signature(
    body: bytes,
    signature_header: Optional[str],
    app_secret: str,
) -> bool:
    """Validate X-Hub-Signature-256 (sha256=<hex>)."""
    if not app_secret or not signature_header:
        return False
    header = signature_header.strip()
    if not header.startswith("sha256="):
        return False
    expected = hmac.new(
        app_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    provided = header[len("sha256=") :]
    return hmac.compare_digest(expected, provided)


def parse_events(
    payload: Mapping[str, Any],
    include: Optional[Iterable[str]] = None,
) -> list[dict[str, Any]]:
    """Flatten Instagram webhook entries into n8n-style event dicts."""
    include_set = {f.strip() for f in include} if include is not None else None
    object_name = payload.get("object") or "instagram"
    events: list[dict[str, Any]] = []

    for entry in payload.get("entry") or []:
        entry_id = entry.get("id")
        entry_time = entry.get("time")
        for change in entry.get("changes") or []:
            field = change.get("field")
            if include_set is not None and field not in include_set:
                continue
            events.append(
                {
                    "object": object_name,
                    "field": field,
                    "value": change.get("value"),
                    "id": entry_id,
                    "time": entry_time,
                }
            )
        for message in entry.get("messaging") or []:
            field = "messages"
            if include_set is not None and field not in include_set:
                continue
            events.append(
                {
                    "object": object_name,
                    "field": field,
                    "value": message,
                    "id": entry_id,
                    "time": entry_time,
                }
            )
    return events
