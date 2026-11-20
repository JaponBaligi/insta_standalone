# `instagram/publisher.py` — container publish pipeline

Shared create → wait → publish flow used by image / reel / story (carousel uses pieces of this).

## What it does
- `create_container` → `POST {node}/media` → container id
- `wait_until_ready` → poll `status_code` until `FINISHED` / `PUBLISHED`
- `publish_container` → `POST {node}/media_publish`
- `publish_media(**params)` → full pipeline

## Limits
- Default wait timeout **300s**, interval **5s** (callers may pass longer, e.g. reels 900s)
- `ERROR` / `EXPIRED` → `MediaProcessingError`
- Timeout → `MediaTimeoutError`
- Media URL must be publicly reachable by Meta (HTTPS)

## How to use

Prefer resource helpers (`image.publish_image`, …). Low-level:

```python
from instagram.publisher import publish_media

publish_media(client, image_url="https://…/a.jpg", caption="Hi")
```
