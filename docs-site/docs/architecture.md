---
sidebar_position: 8
---

# Architecture

High-level layout of the Python package:

| Module | Role |
|--------|------|
| `kindling/app.py` | `Application`: routing (`get` / `post` / `route` / `sse`), `dispatch`, `render` / `render_to_html`, `reactive`, `page`, `run`, `wsgi_app` |
| `kindling/request.py` | Immutable `Request` |
| `kindling/response.py` | `Response`, `html_response`, `json_response`, ... |
| `kindling/config.py` | `KindlingConfig`, `finalize_response`, `finalize_streaming` |
| `kindling/server.py` | HTTP/1.1 via **h11**, threaded `serve()` |
| `kindling/wsgi.py` | `make_wsgi_app` |
| `kindling/live_page.py` | `LivePage`, `KindlingLiveHelper`, element binders, HTML injection |
| `kindling/client_js.py` | Bundles Idiomorph + runtime; serves `/_kindling/client.js` |
| `kindling/reactive.py` | Reactive scope, `expose` / `body`, `signal` / `computed` guards, `bind` / `live` / `on`, SSE snapshot registration |
| `kindling/sse.py` / `kindling/streaming.py` | `SseFanout`, `StreamedHttpResponse`, `@app.sse` wiring |

## Request flow

1. Server reads bytes, builds `Request`, calls `app.dispatch`.
2. Router matches method + path segments; `route_params` merged into `Request`.
3. Handler return normalized to `Response` or `StreamedHttpResponse`.
4. `finalize_response` / `finalize_streaming` add security headers and optional `Server`.

## Signals

Reactive primitives come from the **`signals`** package ([github.com/monster0506/pysignals](https://github.com/monster0506/pysignals): `signal`, `computed`, `effect`). In the Kindling repo that package is checked out as a **git submodule** under `signals/`. Kindling wraps creation of `kindling.signal` / `kindling.computed` outside an active reactive scope with clear errors where applicable.
