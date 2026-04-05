---
sidebar_position: 9
---

# API reference

## Package exports

From `kindling`:

`Application`, `LivePage`, `Request`, `serve`, `make_wsgi_app`

Reactive: `signal`, `computed`, `effect`, `bind`, `body`, `expose`, `live`, `on`

Responses: `Response`, `html_response`, `json_response`, `text_response`, `not_found`, `internal_server_error`

## Application

- `Application(template_dir: str | None = None, config: KindlingConfig = ...)`
- `get(pattern)`, `post(pattern)` - decorators returning the handler
- `route(pattern, methods, handler)`
- `render(template_name, **context) -> Response`
- `render_to_html(template_name, **context) -> str`
- `reactive(name, *, path, template=None)` - context manager (see [Reactive UI](./reactive-ui))
- `page(pattern)` - `LivePage` from callable body without reactive scope
- `sse(pattern)` - SSE from snapshot callable
- `dispatch(req) -> Response | StreamedHttpResponse`
- `run(host=..., port=..., label=..., quiet=...)`
- `wsgi_app` property

## Request

Frozen dataclass: `method`, `path`, `query_string`, `headers`, `body`, `route_params`.

## LivePage (advanced)

Usually created indirectly. Constructor takes `app`, `path`, exactly one of `template_name` or `html_body`, `context` callable, optional `seed_element_handlers`, optional `reactive_stream_url`.

## Client path constant

`kindling.client_js.KINDLING_CLIENT_PATH` is `/_kindling/client.js`.
