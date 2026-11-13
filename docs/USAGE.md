# Using insta_standalone

Python client for the **Instagram Graph API** (`graph.facebook.com`) aimed at
Instagram **Business / Creator** accounts linked to a Facebook Page. It mirrors
the community n8n Instagram node surface (publish, comments, DMs, hashtags,
webhooks) plus insights.

> Unit tests use a fake Graph API. Expect live Meta quirks (permissions, metric
> names, media URL reachability) when you first hit production.

---

## What you need from Meta

1. A Meta developer app with Instagram Graph API access.
2. An Instagram **professional** account linked to a Facebook Page.
3. A **long-lived** Facebook user (or page) access token with scopes such as:
   - `instagram_basic` / `pages_show_list`
   - `instagram_content_publish`
   - `pages_read_engagement`
   - `instagram_manage_comments` (and messaging scopes if you send DMs)
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
print(pages)  # pick a Page id

ig = page.get_instagram_account(client, page_id="<PAGE_ID>")
print(ig["instagram_business_account"]["id"])  # ← put this in IG_NODE
```

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

Run unit tests anytime (no Meta network):

```bash
python -m unittest discover -s instagram/resources/tests -p "test_*.py"
```

---

## Everyday usage

Always create one `GraphClient`, then call resource helpers.

```python
from instagram.client import GraphClient
from instagram.resources import image, reel, story, carousel, comment, messaging
from instagram.resources import hashtag, insights, user

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

Publishing uses create container → poll until ready → `media_publish`. Reels /
stories / carousels default to a longer timeout (900s).

### Comments

```python
comment.list_comments(client, media_id)
comment.create_comment(client, media_id, "Nice shot")
comment.reply_to_comment(client, comment_id, "Thanks!")
comment.hide_comment(client, comment_id)
comment.delete_comment(client, comment_id)
comment.disable_comments(client, media_id)
comment.send_private_reply(client, comment_id, "DM from comment")  # Meta windows apply
```

### Messaging

```python
messaging.send_message(client, recipient_id="<IGSID>", message_text="Hi")
```

Recipient must be an Instagram-scoped ID (usually from a webhook), within Meta’s
messaging windows.

### Hashtags & profile

```python
hid = hashtag.get_hashtag_id(client, "travel")
hashtag.get_recent_media(client, hashtag_id=hid, limit=25)
hashtag.get_top_media(client, hashtag_name="travel", return_all=True)  # capped by max_items (500)

user.get(client)
user.get_media(client, limit=25)
```

### Insights

Metric names change with Meta’s API — pass what your app is allowed to read.

```python
insights.get_account_insights(client, metrics=["reach", "views"], period="day")
insights.get_media_insights(client, media_id, metrics=["likes", "comments", "reach"])
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

### Library helpers

```python
from instagram.webhook import verify_challenge, verify_signature, parse_events

challenge = verify_challenge(query_dict, verify_token="...")
ok = verify_signature(raw_body, header, app_secret="...")
events = parse_events(payload, include={"comments", "messages"})
# each event: {object, field, value, id, time}
```

### Built-in HTTP server

Expose a public HTTPS URL (ngrok, reverse proxy, etc.) to Meta.

```python
from instagram.webhook.server import serve_forever

def on_event(event):
    print(event["field"], event["value"])

serve_forever(host="0.0.0.0", port=8080, on_event=on_event)
# GET/POST http://<host>:8080/webhook
# Needs IG_WEBHOOK_VERIFY_TOKEN + FB_APP_SECRET in the environment
```

In Meta App Dashboard → Webhooks → Instagram:

- Callback URL = your public `/webhook`
- Verify token = same as `IG_WEBHOOK_VERIFY_TOKEN`
- Subscribe to fields you care about (`comments`, `messages`, `mentions`, …)

---

## Package map

| Path | Role |
|------|------|
| `instagram/client.py` | `GraphClient` HTTP + auto-refresh |
| `instagram/config.py` | `.env` → `Config` |
| `instagram/token_store.py` | `token/.token.json` |
| `instagram/publisher.py` | Container create / wait / publish |
| `instagram/resources/*` | Image, reel, story, carousel, comment, messaging, hashtag, user, page, auth, insights |
| `instagram/webhook/` | Challenge, HMAC, parse, stdlib server |
| `instagram/exceptions.py` | `ConfigError`, `GraphAPIError`, `MediaTimeoutError`, `CarouselItemError`, … |

---

## Errors & limits (practical)

- `ConfigError` — missing token / node, or `IG_NODE=me`
- `GraphAPIError` — Meta HTTP error (`code`, `subcode`, `fbtrace_id`)
- `MediaProcessingError` / `MediaTimeoutError` — container never becomes ready
- `CarouselItemError` — which child failed (index + type)
- Auto-refresh failures **warn** and continue with the old token
- Hashtag `return_all=True` stops at `max_items` (default 500)
- Private replies / DMs follow Meta time windows (document those in Meta’s docs)

---

## Related docs

- [README](../README.md) — short overview
