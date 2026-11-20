# `instagram/resources/story.py` — Stories publish

## What it does
- `publish_story(client, video_url=…)` or `publish_story(client, image_url=…)`
- Exactly one of video/image URL
- Optional user tags (username only on stories)

## Limits
- Default timeout **900s**
- Many feed/reel fields are accepted then ignored (warning)
- Stories expire on Instagram as usual; this API only publishes

## How to use

```python
from instagram.resources import story

story.publish_story(client, image_url="https://example.com/s.jpg")
story.publish_story(client, "https://example.com/s.mp4")  # video positional
```
