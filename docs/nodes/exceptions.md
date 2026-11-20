# `instagram/exceptions.py` — error types

| Class | When |
|-------|------|
| `InstagramError` | Base |
| `ConfigError` | Bad / missing `.env` |
| `GraphAPIError` | HTTP/Graph error (`status_code`, `code`, `subcode`, `fbtrace_id`) |
| `MediaProcessingError` | Container ended in `ERROR` / `EXPIRED` |
| `MediaTimeoutError` | Container not ready in time |
| `CarouselItemError` | One carousel child failed (`index`, `media_type`, `__cause__`) |

## How to use

```python
from instagram.exceptions import GraphAPIError, CarouselItemError

try:
    …
except GraphAPIError as e:
    print(e.status_code, e.code, e.subcode)
except CarouselItemError as e:
    print(e.index, e.media_type, e.__cause__)
```
