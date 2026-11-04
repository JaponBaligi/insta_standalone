"""Messaging resource: n8n Instagram node -> Messaging / Send Message.

Meta kisiti: standart mesajlasma penceresinde, yani karsi taraf son 24 saat
icinde hesaba mesaj atmissa gonderilebilir. recipient_id, Instagram-scoped
ID'dir (IGSID), kullanici adi degil.
"""
from __future__ import annotations

import json
from typing import Any

from ..client import GraphClient


def send_message(client: GraphClient, recipient_id: str, message_text: str) -> dict[str, Any]:
    """Messaging / Send Message.

    Cevap: {"recipient_id": ..., "message_id": ...}
    """
    recipient_id = str(recipient_id or "").strip()
    if not recipient_id:
        raise ValueError("recipient_id zorunlu")
    if not str(message_text or "").strip():
        raise ValueError("message_text zorunlu")

    return client.post(
        f"{client.node}/messages",
        recipient=json.dumps({"id": recipient_id}),
        message=json.dumps({"text": message_text}),
    )