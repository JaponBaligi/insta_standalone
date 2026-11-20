# `instagram/client.py` — GraphClient

HTTP client for `graph.facebook.com`. Loads config, attaches the access token, and optionally refreshes it.

## What it does
- `get` / `post` / `delete` → JSON from Graph API
- Injects `access_token` on every call (unless you pass one explicitly)
- Drops `None` params; booleans become `"true"` / `"false"`
- Raises `GraphAPIError` on non-OK responses

## Token behaviour
- Prefers `token/.token.json` over `.env` bootstrap token
- With `FB_APP_ID` + `FB_APP_SECRET` and `auto_refresh=True` (default): learns expiry via `debug_token`, refreshes with `fb_exchange_token` when &lt; **7 days** left
- Refresh failures warn and continue with the old token

## Limits
- Facebook Login tokens only (this repo’s model)
- No retry/backoff beyond refresh soft-fail
- `IG_NODE` comes from config; client does not discover it

## How to use

```python
from instagram.client import GraphClient

client = GraphClient()                 # load_config()
client = GraphClient(auto_refresh=False)
print(client.node, client.token[:6])
client.get("me", fields="id,name")
```
