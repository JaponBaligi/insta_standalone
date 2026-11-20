# insta_standalone

Python Instagram Graph API client (`graph.facebook.com`) for Business/Creator
accounts: publish (image, reel, story, carousel), comments, and Meta webhooks.
Resource layout follows the community n8n Instagram node where applicable.

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
If `me/accounts` is empty, query your Page id directly for `instagram_business_account`.

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

Live smoke (needs real `.env` + media in `test_content/`):

```bash
python test_content/run_live_features.py
```

Unit tests use a fake Graph API; the live runner hits Meta.

## Docs

| Doc | Purpose |
|-----|---------|
| [docs/USAGE.md](docs/USAGE.md) | Setup phases, API examples, webhooks |
| [docs/nodes/](docs/nodes/README.md) | Per-module notes for `instagram/*` |
| [docs/machine/](docs/machine/README.md) | Machine-readable JSON/JSONL docs catalog |
