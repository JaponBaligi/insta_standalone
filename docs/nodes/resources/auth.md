# `instagram/resources/auth.py` — token helpers

## What it does
- `get_me(client)` → `GET /me`
- `exchange_access_token(client, short_lived_token)` → long-lived via `fb_exchange_token`
- `refresh_access_token(client)` → re-exchange current token and save to token store

## Limits
- Needs `FB_APP_ID` + `FB_APP_SECRET` (`ConfigError` otherwise)
- Facebook Login exchange only (not Instagram Login refresh endpoint)
- Long-lived tokens ~60 days; refresh extends the window

## How to use

```python
from instagram.resources import auth

auth.get_me(client)
auth.exchange_access_token(client, short_lived_token="EAA…")
auth.refresh_access_token(client)
```
