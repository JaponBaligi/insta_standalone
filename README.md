# insta_standalone

Python Instagram Graph API client (`graph.facebook.com`) for Business/Creator
accounts: publish (image, reel, story, carousel), comments, messaging, hashtags,
insights, and Meta webhooks. Resource layout follows the community n8n Instagram
node where applicable.

**Full setup and usage:** [docs/USAGE.md](docs/USAGE.md)

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env   # Windows: copy .env.example .env
```

Fill at least:

- `IG_ACCESS_TOKEN` — long-lived Facebook token (`EAA…`)
- `IG_NODE` — Instagram account ID (**not** `me`)

Discover `IG_NODE` with `list_pages()` → `get_instagram_account()` (see the usage guide).

```python
from instagram.client import GraphClient
from instagram.resources import image

client = GraphClient()
image.publish_image(client, "https://example.com/photo.jpg", caption="Hello")
```

## Token notes

- First run bootstraps from `.env`; afterwards `token/.token.json` wins.
- Auto-refresh (near expiry) needs `FB_APP_ID` + `FB_APP_SECRET`.
- To replace a token manually: update `.env` **and** delete `token/.token.json`.

## Tests

```bash
python -m unittest discover -s instagram/resources/tests -p "test_*.py"
```

Not exercised against live Meta — tests use a fake Graph API.

## Docs

| Doc | Purpose |
|-----|---------|
| [docs/USAGE.md](docs/USAGE.md) | Setup phases, API examples, webhooks |
