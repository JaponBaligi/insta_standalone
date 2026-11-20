# `instagram/resources/comment.py` — comments

## What it does
- List: `list_comments` / `iter_comments` / `list_all_comments`
- Moderate: `hide_comment`, `unhide_comment`, `delete_comment`
- Toggle: `disable_comments` / `enable_comments` on media
- Public: `create_comment(media_id, message)`, `reply_to_comment(comment_id, message)`

## Limits
- Only media/comments your IG account owns / can manage
- No private-reply / DM helpers in this repo (removed after live Meta failures)
- Pagination: follow Graph cursors; `max_items` stops early

## How to use

```python
from instagram.resources import comment

comment.create_comment(client, media_id, "Nice")
comment.reply_to_comment(client, comment_id, "Thanks")
comment.hide_comment(client, comment_id)
for c in comment.iter_comments(client, media_id, max_items=50):
    print(c["id"], c.get("text"))
```
