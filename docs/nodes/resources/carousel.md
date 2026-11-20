# `instagram/resources/carousel.py` — carousel / album publish

## What it does
- Normalizes 2–10 items (URL string or `{url, media_type}`)
- Creates child containers, waits, builds parent `CAROUSEL`, publishes
- `CarouselItemError` names which child failed

## Limits
- **2–10** items; URLs validated before any API call
- Default timeout **900s** per wait
- Mix of image/video supported; video children: user tags not supported (warning)
- Caption max 2200 on parent

## How to use

```python
from instagram.resources import carousel

carousel.publish_carousel(
    client,
    items=[
        "https://example.com/1.jpg",
        {"url": "https://example.com/2.mp4", "media_type": "video"},
    ],
    caption="Album",
)
```
