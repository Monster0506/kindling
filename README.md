# Kindling

Small Python web layer built around the [`signals`](./signals) package: routes, Jinja templates, a threaded dev server, WSGI, live pages with optional morph + SSE for reactive UIs.

## Install

From the repo root (uses the local `signals` path dependency):

```bash
uv sync
```

## Quickstart

```python
from kindling import Application, serve

app = Application(template_dir="templates")

@app.get("/hello/{name}")
def hello(req):
    return f"<p>Hello, {req.route_params['name']}</p>"

if __name__ == "__main__":
    serve(app, host="127.0.0.1", port=8000)
```

Or use `app.run(host="127.0.0.1", port=8000)` to print a URL and call `serve`.

## WSGI (production)

```python
# myapp.py
from kindling import Application

app = Application(...)
wsgi_app = app.wsgi_app
```

Run with **waitress**, **gunicorn**, etc., e.g. `gunicorn myapp:wsgi_app`.

**Caveats:** The bundled WSGI adapter returns a single byte string for normal responses. **Streaming responses** (including `text/event-stream` from `app.sse` or reactive `/_kindling/reactive/...`) are not fully supported through this adapter yet; use a server that can speak SSE directly or extend the adapter.

## Live pages and reactive UI

- **`LivePage`**: one URL, GET renders a template, POST runs named `action=` handlers or element bindings, then re-renders.
- **Client script:** `GET /_kindling/client.js` (mounted when you use `LivePage`). In templates, include the script and `{{ kindling_live.binding_tag()|safe }}`.
- **`with app.reactive(...):`**: scoped `signal` / `computed`, plus `bind`, `live`, and `on` decorators. If you use `@bind` or `@live`, Kindling registers **`GET /_kindling/reactive/<scope>`** and the client opens **EventSource** to apply updates.

Use `scope.expose(count=count)` (and similar) to pass reactive values into the Jinja context.

See **REACTIVE_RFC.md** for naming and bind syntax (`bind(selector, "text"|"html"|"json")`).

## Dev server vs SSE

The threaded `serve()` implementation is aimed at local development. Long-lived SSE connections are exercised in tests via `dispatch()`; under a simple threaded socket server, streaming behavior may need further hardening for production.

## Tests

```bash
uv run pytest
```

## Docs

- **ARCHITECTURE.md** — layout of packages and request flow.
- **REACTIVE_RFC.md** — reactive scope, bind/live/on, transport.
- **implementation.md** — ordered build plan used for this codebase.
