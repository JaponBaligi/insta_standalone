# Using insta_standalone

Python client for the **Instagram Graph API** (`graph.facebook.com`) aimed at
Instagram **Business / Creator** accounts linked to a Facebook Page. Supported
surface: publish (image, reel, story, carousel), comments, auth/page helpers,
and Meta webhooks.

> Unit tests use a fake Graph API. Use `test_content/run_live_features.py` against
> a real token when you need end-to-end proof.

---

## What you need from Meta

1. A Meta developer app with Instagram Graph API access.
2. An Instagram **professional** account linked to a Facebook Page.
3. A **long-lived** Facebook user access token with scopes such as:
   - `instagram_basic` / `pages_show_list`
   - `instagram_content_publish`
   - `pages_read_engagement`
   - `instagram_manage_comments`
4. `FB_APP_ID` + `FB_APP_SECRET` if you want automatic token refresh or webhooks.

Use [Graph API Explorer](https://developers.facebook.com/tools/explorer/) or your
own OAuth flow to create a short-lived token, then exchange it for a long-lived
one (`~60` days). Tokens typically start with `EAA`.

---

## Setup phases

### Phase 1 — Install

```bash
cd insta_standalone
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Dependencies: `requests`, `python-dotenv`.

### Phase 2 — Configure `.env`

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

| Variable | Required | Purpose |
|----------|----------|---------|
| `IG_ACCESS_TOKEN` | Yes (first run) | Bootstrap token; ignored once `token/.token.json` exists |
| `IG_NODE` | Yes | Instagram account ID — **must not** be `me` |
| `IG_GRAPH_API_VERSION` | No | Default `v25.0` |
| `FB_APP_ID` / `FB_APP_SECRET` | For refresh / webhooks | Token exchange + `X-Hub-Signature-256` |
| `IG_WEBHOOK_VERIFY_TOKEN` | For webhooks | Must match Meta App Dashboard verify token |

### Phase 3 — Discover `IG_NODE`

`IG_NODE` is the Instagram business account id, not the Facebook user.

```python
from instagram.client import GraphClient
from instagram.resources import page

client = GraphClient()  # reads .env
pages = page.list_pages(client)
print(pages)  # pick a Page id (may be [] with granular Page tokens)

ig = page.get_instagram_account(client, page_id="<PAGE_ID>")
print(ig["instagram_business_account"]["id"])  # ← put this in IG_NODE
```

If `me/accounts` is empty, use Page ids from `debug_token` → `granular_scopes`
and call `get_instagram_account` with each Page id until you see
`instagram_business_account`.

Set `IG_NODE` in `.env`, then recreate the client (or restart your process).

### Phase 4 — Token store & auto-refresh

1. First successful client use with only `.env` bootstraps from `IG_ACCESS_TOKEN`.
2. With `FB_APP_ID` + `FB_APP_SECRET`, the client calls `debug_token`, stores
   expiry in `token/.token.json`, and **auto-refreshes** when less than **7 days**
   remain (`fb_exchange_token`).
3. Stored token **wins** over `.env` on later runs.
4. To force a new token: update `IG_ACCESS_TOKEN` **and delete**
   `token/.token.json`.

`token/` is gitignored.

### Phase 5 — Smoke check

```python
from instagram.client import GraphClient
from instagram.resources import auth, user

client = GraphClient()
print(auth.get_me(client))
print(user.get(client))
```

```bash
python -m unittest discover -s instagram/resources/tests -p "test_*.py"
python test_content/run_live_features.py
```

### Automation trigger (Telegram → publish)

```bash
# .env: AUTOMATION_TOKEN=long-random-secret
python -m instagram.runner serve --port 8787
```

```http
POST /v1/publish
Authorization: Bearer <AUTOMATION_TOKEN>
Content-Type: application/json

{"type":"image","image_url":"https://example.com/a.jpg","caption":"from telegram"}
```

One-shot without HTTP:

```bash
python -m instagram.runner publish --file job.json
```

See [nodes/automation.md](nodes/automation.md).

---

## Everyday usage

```python
from instagram.client import GraphClient
from instagram.resources import image, reel, story, carousel, comment, user

client = GraphClient()
```

Media URLs must be **publicly fetchable by Meta** (HTTPS).

### Publish

```python
image.publish_image(client, "https://example.com/photo.jpg", caption="Hello")

reel.publish_reel(client, "https://example.com/video.mp4", caption="Reel")

story.publish_story(client, image_url="https://example.com/story.jpg")
# or: story.publish_story(client, video_url="https://example.com/story.mp4")

carousel.publish_carousel(
    client,
    items=[
        {"url": "https://example.com/1.jpg"},
        {"url": "https://example.com/2.mp4", "media_type": "video"},
    ],
    caption="Album",
)
```

### Comments

```python
comment.list_comments(client, media_id)
comment.create_comment(client, media_id, "Nice shot")
comment.reply_to_comment(client, comment_id, "Thanks!")
comment.hide_comment(client, comment_id)
comment.delete_comment(client, comment_id)
comment.disable_comments(client, media_id)
comment.enable_comments(client, media_id)
```

### Profile

```python
user.get(client)
user.get_media(client, limit=25)
```

### Auth helpers

```python
from instagram.resources import auth

auth.get_me(client)
auth.exchange_access_token(client, short_lived_token="...")
auth.refresh_access_token(client)  # re-exchange + persist
```

---

## Webhooks

```python
from instagram.webhook import verify_challenge, verify_signature, parse_events

challenge = verify_challenge(query_dict, verify_token="...")
ok = verify_signature(raw_body, header, app_secret="...")
events = parse_events(payload, include={"comments", "messages"})
```

```python
from instagram.webhook.server import serve_forever

def on_event(event):
    print(event["field"], event["value"])

serve_forever(host="0.0.0.0", port=8080, on_event=on_event)
```

Needs `IG_WEBHOOK_VERIFY_TOKEN` + `FB_APP_SECRET`. Point Meta’s Instagram
webhook callback at your public `/webhook` URL.

---

## Package map

| Path | Role |
|------|------|
| `instagram/client.py` | `GraphClient` HTTP + auto-refresh |
| `instagram/config.py` | `.env` → `Config` |
| `instagram/token_store.py` | `token/.token.json` |
| `instagram/publisher.py` | Container create / wait / publish |
| `instagram/resources/*` | Image, reel, story, carousel, comment, user, page, auth |
| `instagram/webhook/` | Challenge, HMAC, parse, stdlib server |
| `instagram/exceptions.py` | `ConfigError`, `GraphAPIError`, `MediaTimeoutError`, `CarouselItemError`, … |

---

## Errors & limits (practical)

- `ConfigError` — missing token / node, or `IG_NODE=me`
- `GraphAPIError` — Meta HTTP error (`code`, `subcode`, `fbtrace_id`)
- `MediaProcessingError` / `MediaTimeoutError` — container never becomes ready
- `CarouselItemError` — which child failed (index + type)
- Auto-refresh failures **warn** and continue with the old token

---

## Related docs

- [README](../README.md) — short overview
- [nodes/](nodes/README.md) — per-module notes (limits + usage)
- [machine/](machine/README.md) — machine-readable JSON/JSONL mirror of docs/
