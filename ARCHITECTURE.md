# Kindling architecture

## Layout

- **`kindling/app.py`** — `Application`: routing (`get` / `post` / `route` / `sse`), `dispatch`, `render`, `reactive`, `run`, `wsgi_app`.
- **`kindling/request.py`** / **`kindling/response.py`** — immutable-ish `Request`, `Response`, and small factories (`html_response`, `json_response`, etc.).
- **`kindling/config.py`** — `KindlingConfig`, `finalize_response`, `finalize_streaming`.
- **`kindling/server.py`** — HTTP/1.1 via **h11**, threaded `serve()`.
- **`kindling/wsgi.py`** — `make_wsgi_app` for WSGI servers.
- **`kindling/live_page.py`** — `LivePage`, element `id` bindings, Jinja `kindling_live` helper.
- **`kindling/client_js.py`** — embedded morph client, `/_kindling/client.js`.
- **`kindling/reactive.py`** — reactive scope, `signal` / `computed` guards, `bind` / `live` / `on`, SSE snapshot registration.
- **`kindling/sse.py`** / **`kindling/streaming.py`** — `SseFanout`, `StreamedHttpResponse`, `@app.sse`.

## Request flow

1. **Dev server** or **WSGI** builds a `Request` (method, path, query, headers, body).
2. **`Application.dispatch`** matches a route, runs the handler, normalizes `str`/`bytes`/`Response`/`StreamedHttpResponse`.
3. **`finalize_response`** / **`finalize_streaming`** adds default security headers (and optional `Server`) unless already set.
4. Adapter writes status, headers, and body (or streams for `StreamedHttpResponse` where supported).

## Dependency

**`signals`** (git submodule / path dependency) provides `signal`, `computed`, and `effect`. Kindling re-exports `effect` without a scope requirement; `kindling.signal` / `kindling.computed` require an active `app.reactive` block.
