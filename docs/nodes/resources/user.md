# `instagram/resources/user.py` — IG profile & media list

Operates on `client.node` (the Instagram account id).

## What it does
- `get(client)` → profile fields (username, counts, picture, …)
- `get_media(client, limit=25)` → owned media page

## Limits
- Token must be allowed to manage that IG user (Page-linked Business/Creator)
- Wrong `IG_NODE` → Graph `#100` / subcode `33`

## How to use

```python
from instagram.resources import user

print(user.get(client)["username"])
print(user.get_media(client, limit=5))
```
