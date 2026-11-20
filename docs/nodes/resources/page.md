# `instagram/resources/page.py` — Page → IG account

## What it does
- `list_pages(client)` → `GET me/accounts`
- `get_instagram_account(client, page_id)` → Page fields including `instagram_business_account`

## Limits
- With granular Page tokens, `list_pages` may return **`data: []`** even when Pages are granted — call `get_instagram_account` with known Page ids (from `debug_token` granular `target_ids`)
- Page must be linked to an IG professional account or `instagram_business_account` is missing

## How to use

```python
from instagram.resources import page

pages = page.list_pages(client)
ig = page.get_instagram_account(client, "1155820267610084")
node = ig["instagram_business_account"]["id"]  # → IG_NODE
```
