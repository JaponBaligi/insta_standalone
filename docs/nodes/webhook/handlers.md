# `instagram/webhook/handlers.py` — verify & parse

Pure helpers (no HTTP server).

## What it does
- `verify_challenge(query, verify_token)` — Meta GET subscription handshake → challenge string or `ValueError`
- `verify_signature(body, X-Hub-Signature-256, app_secret)` — HMAC-SHA256
- `parse_events(payload, include=…)` — flatten `entry[].changes[]` and `entry[].messaging[]` into `{object, field, value, id, time}`

## Limits
- Signature requires raw request body bytes
- `include` filters by field name (`comments`, `messages`, …)
- Does not call Graph API

## How to use

```python
from instagram.webhook import verify_challenge, verify_signature, parse_events

challenge = verify_challenge(query, verify_token="secret")
ok = verify_signature(raw_body, header, app_secret)
events = parse_events(payload, include={"comments"})
```
