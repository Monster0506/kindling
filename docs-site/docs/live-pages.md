---
sidebar_position: 4
---

# Live pages

A **LivePage** binds **one path** to:

1. **GET** - render a Jinja template **or** a Python `html_body` callable (`str` or `Response`).
2. **POST** - run an **action** (`action=` field) or an **element binding** (`kindling_target` + `kindling_event`), then **re-render** the same page.

Creating a `LivePage` (directly or via `app.reactive` / `app.page`) mounts `GET /_kindling/client.js`, which performs `fetch` POSTs and **morphs** the document with **Idiomorph** when the `X-Requested-With: kindling-live` header is present.

## Jinja templates

Pass a template name and a **context factory** (or dict-like callable). Templates receive `kindling_live` - a helper with `binding_tag()` that emits the JSON config element for the client.

If the rendered HTML omits `kindling-live-config` and the client script, Kindling **injects** them immediately before `</body>` (case-insensitive).

Use the `unwrap` Jinja filter for signal values in the first paint: `{{ count|unwrap }}`.

## `html_body` callables

Handlers may take `()`, `(req)`, or `(req, kindling_live)` and return `str` or `Response`. String bodies get the same auto-injection as Jinja output when fragments are missing.

## POST actions

Register named actions:

```python
@page.action
def save(req):
    pass
```

Forms post `action=save` (or use `data-kindling-action` on buttons - see client docs).

## Element bindings (`@on`)

Inside `app.reactive`, `@on("element-id", "click")` registers a handler for that element. The client POSTs with `kindling_target` and `kindling_event` so the server can dispatch without a named `action`.

## `app.page` without reactive

`@app.page("/path")` registers a **LivePage** with **no** reactive scope - useful for static or hand-written HTML that still benefits from morph + optional injection.
