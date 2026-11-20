# `instagram/resources/reel.py` — Reels publish

## What it does
- `build_reel_params` / `publish_reel(client, video_url, caption=…)`
- Supports cover, share_to_feed, thumb offset, collaborators, tags, trial reels (`MANUAL` / `SS_PERFORMANCE`)

## Limits
- Default timeout **900s** (video processing is slow)
- Public `video_url` required
- `alt_text` accepted for parity but not sent (API is image-oriented)
- `cover_url` + `thumbnail_offset` together may warn

## How to use

```python
from instagram.resources import reel

reel.publish_reel(client, "https://example.com/v.mp4", caption="Reel")
```
