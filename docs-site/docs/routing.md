---
sidebar_position: 3
---

# Routing and requests

## Registering routes

Use decorators on callables that accept a [`Request`](./api#request) instance:

```python
@app.get("/items/{id}")
def item(req):
    return json_response({"id": req.route_params["id"]})

@app.post("/items")
def create_item(req):
    pass
```

Patterns are split on `/`. Dynamic segments use `{name}` and populate `req.route_params`.

## Handler return types

Handlers may return:

| Type | Behavior |
|------|----------|
| `Response` | Used as-is (after config finalization) |
| `StreamedHttpResponse` | Chunked streaming (dev server) |
| `str` | Wrapped as HTML (`text/html`) |
| `bytes` | Wrapped as `application/octet-stream` |

Helpers include `html_response`, `json_response`, `text_response`, `not_found`, `bad_request`, and `internal_server_error`.

## Request

- `req.method`, `req.path`, `req.query_string`, `req.headers`, `req.body`
- `req.route_params` - path parameters
- `req.header(name, default=None)`
- `req.form`, `req.form_value(name)` - `application/x-www-form-urlencoded`
- `req.query(name)` - query string
- `req.json_body()` - JSON body (UTF-8)

## SSE routes

`@app.sse("/path")` registers a streaming GET that yields snapshot dictionaries as Server-Sent Events. See [Reactive UI](./reactive-ui) for how reactive scopes reuse this mechanism.
