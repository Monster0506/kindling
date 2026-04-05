---
sidebar_position: 7
---

# Demo applications

Run from the **repository root** with `uv run` so `kindling` resolves:

```bash
uv sync
uv run python demos/routes/app.py
uv run python demos/counter/app.py
uv run python demos/guestbook/app.py
uv run python demos/pulse/app.py
```

Default ports: **8000** (routes), **8001** (counter), **8002** (guestbook), **8003** (pulse). Change `app.run(..., port=...)` if needed.

| Demo | Highlights |
|------|------------|
| **routes** | Reactive `/` with `@bind` / `@on`; `GET /api/hello` returns JSON including shared `count` (`signals.signal`). |
| **counter** | Full reactive counter; `@body` on `/about`; `app.page` on `/def`. |
| **guestbook** | `@bind("#entries", "html")` and `@on` for the form. |
| **pulse** | `@live` payload + `kindling-live` listener; background **wall** signal for periodic ticks. |

See source under `demos/<name>/` and templates in `demos/<name>/templates/`.
