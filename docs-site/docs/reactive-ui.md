---
sidebar_position: 5
---

# Reactive UI

## Scopes

```python
with app.reactive("my_scope", path="/", template="index.html"):
    count = signal(0)
    expose(count=count)

    @bind("#readout", "text")
    def readout() -> str:
        return str(count.value)

    @on("inc", "click")
    def inc_click() -> None:
        count.value += 1
```

Rules:

- **Nested** `with app.reactive(...)` on the same task is an error.
- **Duplicate** scope **name** or **path** across successful exits is an error.
- You must pass either `template=...` or exactly one **`@body`** handler, not both.
- `kindling.signal` and `kindling.computed` require an **active** reactive scope. For values shared outside the block (for example a JSON route), use `signals.signal` from the `signals` package so computeds and `bind` still read `.value` consistently.

## `expose`

`expose(name=value, ...)` merges names into the Jinja context for the first paint (and keeps objects available server-side). With `as scope`, use `scope.expose(...)`.

## `bind(selector, mode)`

`mode` is `text`, `html`, or `json`. The decorated function is wrapped in a **computed**; when dependencies change, Kindling pushes updates over SSE to matching `document.querySelector(selector)` nodes.

Selectors must match a **single** element; use IDs (`#id`) in practice.

## `live(key)`

Exposes a computed **object** under `msg.live[key]` in the SSE payload. The client dispatches a `kindling-live` `CustomEvent` with `detail` set to the **full** live map when any `@live` value changes.

Use a **reactive** dependency if you need periodic recomputation (for example a toggling `signals.signal` updated from a background thread) because wall-clock time alone is not tracked.

## `on(element_id, event)`

Registers POST handlers for `kindling_target` + `kindling_event` (for example `click`, `submit`). Event names are normalized to lower case.

## `@body`

Module-level `body` (or `scope.body`) registers raw HTML for the scope when `template=` is omitted.

## Transport

If the scope has any `@bind` or `@live`, Kindling registers:

`GET /_kindling/reactive/<url-encoded-scope-name>`

The client opens **EventSource** on that URL and applies JSON snapshots: `binds` for DOM updates, `live` for `kindling-live` events.
