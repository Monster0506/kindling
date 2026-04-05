---
sidebar_position: 2
---

# Getting started

## Requirements

- Python **3.12+**
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Install

**signals** is a separate package ([pysignals](https://github.com/monster0506/pysignals)). This repo vendors it with **git** at `signals/` (submodule). Clone with submodules, then from the **repository root**:

```bash
git submodule update --init --recursive
uv sync
```

If you cloned with `git clone --recurse-submodules`, the submodule step is already done.

## Minimal app

```python
from kindling import Application, serve

app = Application(template_dir="templates")

@app.get("/hello/{name}")
def hello(req):
    return f"<p>Hello, {req.route_params['name']}</p>"

if __name__ == "__main__":
    serve(app, host="127.0.0.1", port=8000)
```

`Application.run(host=..., port=...)` prints a URL and calls `serve()` for you.

## Run tests

```bash
uv run pytest
```

## WSGI and streaming

Expose `app.wsgi_app` to servers such as waitress or gunicorn:

```python
from kindling import Application

app = Application(...)
wsgi_app = app.wsgi_app
```

The bundled WSGI adapter materializes a **single** response body. **Streaming** responses (for example `text/event-stream` from reactive `/_kindling/reactive/...` or `app.sse`) are not fully adapted for generic WSGI yet; use the dev server, a server that supports streaming natively, or extend the adapter.

## This documentation site

From `docs-site/`:

```bash
npm install
npm start
```

Build static output:

```bash
npm run build
npm run serve
```
