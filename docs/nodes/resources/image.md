# `instagram/resources/image.py` — feed image publish

## What it does
- Builds container params (caption, alt_text, collaborators, location, user/product tags)
- `publish_image(client, image_url, caption=…)` → full publish pipeline
- Also exports tag helpers and `build_reel_extras` used by reels

## Limits
- Caption max **2200** chars
- `image_url` must be public HTTPS (Meta fetches it)
- Default publish timeout **300s**
- Reel-only fields on an image container are ignored (warning)
- User/product tag positions must be 0.0–1.0

## How to use

```python
from instagram.resources import image

image.publish_image(
    client,
    "https://example.com/photo.jpg",
    caption="Hello",
    alt_text="A photo",
)
```
