# Machine-readable docs

Generated mirror of human documentation under `docs/` (excludes `docs/superpowers/` and this folder).

| File | Use |
|------|-----|
| `index.json` | Lightweight routing (no bodies) |
| `catalog.json` | Full catalog including `content` |
| `documents.jsonl` | One document object per line |
| `schema.json` | Field / file descriptions |

Regenerate after editing `docs/**/*.md`:

```bash
python docs/machine/generate.py
```
