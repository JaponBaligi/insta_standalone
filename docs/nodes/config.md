# `instagram/config.py` — Config

Reads `.env` into a frozen `Config` dataclass.

## What it does
- Required: `IG_ACCESS_TOKEN`, `IG_NODE`
- Optional: `IG_GRAPH_API_VERSION` (default `v25.0`), `FB_APP_ID`, `FB_APP_SECRET`
- `base_url` → `https://graph.facebook.com/{version}`

## Limits
- `IG_NODE` cannot be empty or `me` (`ConfigError`) — `me` is the Facebook user, not the IG account
- Does not validate that the node exists on Meta

## How to use

```python
from instagram.config import load_config

cfg = load_config()
print(cfg.node, cfg.base_url)
```

Usually you never call this directly — `GraphClient()` calls `load_config()`.
