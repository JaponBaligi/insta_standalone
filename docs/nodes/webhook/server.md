# `instagram/webhook/server.py` — stdlib webhook HTTP

## What it does
- `make_handler(verify_token=…, app_secret=…, on_event=…)` → `BaseHTTPRequestHandler`
- `serve_forever(host, port, …)` — blocks; defaults credentials from `IG_WEBHOOK_VERIFY_TOKEN` + `FB_APP_SECRET`
- `GET /webhook` — challenge; `POST /webhook` — verify signature, parse, call `on_event` per event

## Limits
- Single-threaded `http.server` — fine for smoke / low traffic, not production scale
- Needs a **public HTTPS** URL in front (ngrok, reverse proxy, …) for Meta
- No persistence; your `on_event` must handle work

## How to use

```python
from instagram.webhook.server import serve_forever

def on_event(event):
    print(event["field"], event["value"])

serve_forever(host="0.0.0.0", port=8080, on_event=on_event)
```
