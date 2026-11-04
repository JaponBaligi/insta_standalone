# insta_standalone

Instagram Graph API client in Python (image, reel, story, carousel, comment,
messaging, hashtag). Uses `graph.facebook.com` with a long-lived Facebook
token (starts with `EAA`) and the Facebook token-exchange flow.

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill it in.

### IG_NODE (required)

`IG_NODE` must be your **Instagram account ID**. It is always read from `.env`;
if it is missing, empty or `me`, the program stops with a `ConfigError`.
With a Facebook-login token `me` is the Facebook user, not the Instagram
account, so publishing and hashtag calls would break.

To find the ID: call `resources/page.py` `list_pages()` to get your Page ID,
then `get_instagram_account(client, page_id)`. The `instagram_business_account.id`
in the response is the value for `IG_NODE`.

### Token flow

- `IG_ACCESS_TOKEN` in `.env` is only used the **first time** (bootstrap).
- After that the token lives in `token/.token.json` (path is fixed to the
  project root, so running from another directory or over SSH uses the same file).
  The stored token takes priority over `.env`, and it is refreshed automatically
  when it gets close to expiry (needs `FB_APP_ID` and `FB_APP_SECRET`).
- **To replace the token by hand**, pasting it into `.env` is not enough:
  also delete `token/.token.json`.
- `token/` is in `.gitignore`.

### Other settings

- `IG_GRAPH_API_VERSION` defaults to `v25.0`.
- Hashtag `get_recent_media` / `get_top_media` with `return_all=True` stop at
  `max_items` (default 500).
- A failing carousel child raises `CarouselItemError` with its position and
  type (e.g. "Carousel item 3 (video) failed: ..."); item URLs are checked
  before any API call.

## Not tested against real Meta

Everything was only tested against a fake Graph API.