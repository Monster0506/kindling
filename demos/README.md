# Kindling demos

Run from the **repository root** with the project environment (so `kindling` resolves):

```bash
uv sync
uv run python demos/routes/app.py
uv run python demos/counter/app.py
uv run python demos/guestbook/app.py
uv run python demos/pulse/app.py
```

Each app prints a URL. Default ports are **8000** (routes), **8001** (counter), **8002** (guestbook), **8003** (pulse) so you can run several at once. Edit `app.run(..., port=...)` if a port is taken.

## Idiomatic pattern (HTML demos)

1. `**with app.reactive("name", path="...", template="..."):`** - registers the LivePage and optional SSE stream when you use `@bind` / `@live` (optional `**as scope**` if you prefer `**scope.expose**` / `**@scope.body**`).
2. `**count = signal(...)**` - use `**kindling.signal**` (re-exported from `kindling`), not `signals.signal`.
3. `**expose(count=count, ...)**` - pass values into the Jinja first paint (or `**scope.expose(...)**` with `**as scope**`).
4. `**@bind("#id", "text"|"html"|"json")**` - computed fragments pushed over SSE and applied to the DOM.
5. `**@on("element-id", "click"|"submit"|...)**` - POST handlers for that LivePage route.
6. `**@body**` (optional) - omit `template=` and return raw HTML from a function; see **REACTIVE_RFC.md**. **counter** uses this for `/about`.
7. `**@app.page("/path")`** (optional) - a **LivePage** with no `**reactive`** block; **counter** `/def`.

Plain `**@app.get` / `@app.post`** remain valid for non-UI routes (e.g. JSON APIs in **routes**).


| Demo          | What it shows                                                       |
| ------------- | ------------------------------------------------------------------- |
| **routes**    | Reactive home + `@bind` / `@on`; `/api/hello` JSON includes shared `count`. |
| **counter**   | `@bind` / `@on` on `/`; `@body` on `/about`; `**app.page`** `/def`. |
| **guestbook** | `@bind("#entries", "html")` for the list, `@on` for the form.       |
| **pulse**     | Same pattern + `@live` and a `kindling-live` event listener.        |


