# Automation trigger (inbound publish API)

Telegram / external dashboards call this project to publish.

## HTTP
- `GET /health` — no auth
- `POST /v1/publish` — `Authorization: Bearer $AUTOMATION_TOKEN`
- Body: job JSON (`type`, urls, caption, …) — see runner help

## CLI
```bash
python -m instagram.runner serve --host 0.0.0.0 --port 8787
python -m instagram.runner publish --file job.json
python -m instagram.runner publish --json "{\"type\":\"image\",\"image_url\":\"https://…\"}"
```

## Env
- `AUTOMATION_TOKEN` — required for HTTP publish
- Existing `IG_*` / `FB_*` for Graph publish

## Limits
- Sync: waits for Meta container processing (can be minutes for video)
- Media URLs must be public HTTPS
- No queue / retry in v1
