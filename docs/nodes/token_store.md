# `instagram/token_store.py` — persistent token

Stores the live access token under project-root `token/.token.json` (gitignored).

## What it does
- `load()` / `save(token, expires_in)` / `seconds_left(data)`
- Path is fixed from package location so CWD does not matter

## Limits
- Single global file for the project
- If `expires_at` is missing, auto-refresh will not trigger on expiry
- Corrupt JSON → `load()` returns `None`

## How to use

```python
from instagram import token_store

token_store.save("EAA…", expires_in=5_184_000)
data = token_store.load()
print(token_store.seconds_left(data))
```

To force `.env` bootstrap again: delete `token/.token.json`.
