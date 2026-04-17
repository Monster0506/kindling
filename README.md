# Kindling

Small Python web layer built around **[signals](https://github.com/monster0506/pysignals)** (`signal`, `computed`, `effect`): routes, Jinja templates, a threaded dev server, WSGI, live pages with optional morph + SSE for reactive UIs. The dependency is wired into this repo as a **git submodule** at [`signals/`](./signals) (see [`.gitmodules`](./.gitmodules)).

## Install

Clone with submodules, then sync:

```bash
git clone --recurse-submodules <repo-url>
cd kindling
# If you already cloned without submodules:
git submodule update --init --recursive

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

- **`LivePage`**: one URL, GET renders a **template** or an **`html_body`** callable, POST runs named `action=` handlers or element bindings, then re-renders.
- **Client script:** `GET /_kindling/client.js` (mounted when you use `LivePage`). POST responses are merged into the live DOM with **Idiomorph** (vendored, 0BSD). For **LivePage** (Jinja, **`@body`**, **`app.page`**), Kindling injects `kindling-live-config` and that script before `</body>` when missing. Inline scripts after a morph are re-run via a small Kindling hook (use one-time guards for `window` listeners). You can still call `{{ kindling_live.binding_tag()|safe }}` for a custom placement.
- **`@app.reactive(name, path=..., template=...)`**: decorator that registers a **per-connection** reactive scope. The decorated function is called fresh for each browser connection, creating isolated signal graphs — so each user has their own state. Use `signal`, `computed`, `bind`, `live`, `on`, and `expose` inside it. If you use `@bind` or `@live`, Kindling registers **`GET /_kindling/reactive/<scope>?conn=<id>`** and the client opens **EventSource** to apply updates.
- **`app.page("/path")`**: registers a **`LivePage`** with no reactive scope (static or hand-written HTML).

Use **`expose(count=count)`** inside the reactive factory to pass values into the Jinja context.

```python
@app.reactive("counter", path="/", template="index.html")
def _():
    count = signal(0)
    expose(count=count)

    @bind("#readout", "text")
    def readout() -> str:
        return str(count.value)

    @on("inc", "click")
    def inc() -> None:
        count.value += 1
```

See **REACTIVE_RFC.md** for naming and bind syntax (`bind(selector, "text"|"html"|"json")`). Example apps live under **`demos/`** (see **`demos/README.md`**).

## Dev server vs SSE

The threaded `serve()` implementation is aimed at local development. Long-lived SSE connections are exercised in tests via `dispatch()`; under a simple threaded socket server, streaming behavior may need further hardening for production.

## Tests

```bash
uv run pytest
```

## Docs

**Docusaurus site** (guides + API overview): see [`docs-site/`](./docs-site/). From that directory run `npm install`, `npm start`, or `npm run build`.

- **demos/README.md** - how to run the sample apps under `demos/`.
