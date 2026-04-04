# Kindling reactive UI (RFC)

## Naming

Public URLs and JSON keys visible to authors use the `**kindling**` prefix (for example `/_kindling/client.js`, `/_kindling/reactive/<scope>`). Client requests may send `X-Requested-With: kindling-live`.

## Reactive scope

```python
from kindling import expose, signal

with app.reactive("scope_name", path="/", template="index.html"):
    count = signal(0)
    expose(count=count)
```

You can still use `**as scope**` and call `**scope.expose(...)**` if you prefer.

### Raw HTML without a template file

Omit `template=` and register exactly one `**@body**` handler (import `**body**` from `**kindling**`). It may take `()`, `(req)`, or `(req, kindling_live)` and must return `str` or `Response`.

For **`str`** responses, Kindling injects **`kindling_live.binding_tag()`** (the JSON config) and **`<script src="/_kindling/client.js" defer>`** immediately before the last **`</body>`** (case-insensitive), but only if those pieces are not already present in the string. That matches what Jinja templates do manually with `{{ kindling_live.binding_tag()|safe }}` plus the script. You can still call **`kindling_live.binding_tag()`** yourself if you need a custom placement, or return **`Response`** to bypass injection entirely.

```python
from kindling import body

with app.reactive("about", path="/about"):

    @body
    def about_html(_req) -> str:
        return """<!DOCTYPE html><html><body>
        <p>About</p>
        </body></html>"""
```

### LivePage without a reactive scope

`**app.page(path)**` registers a **`LivePage`** whose body is a plain function — no **`with app.reactive`**, no **`signal` / `@bind`**. String bodies get the same automatic config + client script injection as **`@body`**.

`**@scope.body**` is the same as `**@body**` when you use `**as scope**`. You cannot combine `template=` with `**@body**` / `**@scope.body**`.

- **Nested** `with app.reactive(...)` on the same task raises.
- **Duplicate** scope **name** or **path** across successful exits raises.
- `**kindling.signal` / `kindling.computed`** outside an active scope raise with a clear error.
- `**kindling.reactive.effect**` (re-exported as `**kindling.effect**`) has no scope requirement.

## Template context

Expose values to Jinja explicitly:

```python
expose(count=count, lines=lines)
# or: scope.expose(count=count, lines=lines)
```

Use the `**unwrap**` filter for signal-like objects: `{{ count|unwrap }}`.

## `bind`, `live`, `on`

Imported from `**kindling**` or `**kindling.reactive**`:

- `**bind(selector, mode)**` — `mode` is the second **positional** argument: `"text"`, `"html"`, or `"json"` (Python’s `as` cannot be a keyword argument name). Registers a **computed** whose value is pushed over SSE and applied with `querySelector(selector)` on the client.
- `**live(key)`** — registers a computed payload merged into SSE under `live`; the client dispatches a `**kindling-live**` `CustomEvent` with `detail` set to the `live` object.
- `**on(element_id, event)**` — registers handlers merged into `**LivePage**` element bindings (`click`, `submit`, …). POST bodies use `kindling_target` and `kindling_event`.

## Live page actions

- Legacy **named actions**: POST field `**action=<function_name>`** matching `@page.action`.
- **Element bindings**: `kindling_target=<id>&kindling_event=click|submit|...`.

## Client runtime

- `**GET /_kindling/client.js`** — morph updated HTML into `document.body` after POST; attaches listeners from the JSON config in `**kindling-live-config**`.
- If `**reactiveUrl**` is present in that config, opens `**EventSource(reactiveUrl)**` and applies `bind` / `live` payloads.

## SSE snapshot shape

Reactive streams emit JSON like:

```json
{
  "binds": { "#selector": { "mode": "text", "value": "..." } },
  "live": { "key": "..." }
}
```

## Production notes

Use a production WSGI/ASGI stack that supports **chunked** or streaming responses for SSE. Kindling’s minimal WSGI adapter is oriented toward buffered responses; see **README.md** caveats.
