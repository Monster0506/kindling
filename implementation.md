# Kindling — implementation guide

This document is a **build order** for the **Kindling** web layer (working name; replace the old app-server package in this repo). `**signals` already exists** and stays as a dependency — do not reimplement it.

Each section is **one git commit** (or a very small series if you prefer splitting tests). After each commit, run the test suite and fix failures before moving on.

**Convention:** subsections titled **“What app authors can do now”** show only **user-facing** code — how someone builds an app with Kindling. They are **not** samples of framework internals.

---

## Commit 1 — Project shell and package name

**Implement**

- Add `kindling` as an importable package (empty `__init__.py` or re-export stub).
- Point `pyproject.toml` at the new package (and keep `signals` as a dependency with its existing constraints).
- Wire `pytest` (and optionally `uv` workflow) so `uv run pytest` succeeds with zero tests or a single smoke test (`import kindling`).

**Test**

- `uv run pytest` passes.

**Suggested message:** `chore: kindling package skeleton and test runner`

### What app authors can do now

Nothing useful yet — the package imports. They would still only `import kindling` to verify install.

---

## Commit 2 — Request and Response

**Implement**

- Immutable (or clearly documented) **request** type: method, path, query string, headers, body; helpers such as parsing `application/x-www-form-urlencoded` into field access.
- **Response** type: status, header list, body bytes; factories for HTML, plain text, JSON, 404, 500.

**Test**

- Unit tests: build a request with a synthetic body and read form fields; build responses and assert status and body.

**Suggested message:** `feat(kindling): Request and Response types`

### What app authors can do now

Still no HTTP server — authors only benefit indirectly once routing exists. No example required.

---

## Commit 3 — Router and bare Application

**Implement**

- Route table: match path patterns (at least static paths and `{name}` segments), method sets, and attach callables.
- **Application** with `get` / `post` decorators (or equivalent) registering handlers.
- **Dispatch**: given a request, find handler, invoke it, normalize return values (e.g. allow `str` or `Response`).

**Test**

- GET returns 404 when unmatched.
- Registered GET returns 200 and expected body.
- Route params appear on the request object for templated paths.

**Suggested message:** `feat(kindling): Router and Application dispatch`

### What app authors can do now

They can register plain HTTP handlers (once something can call `dispatch`; see next commits). Conceptually:

```python
from kindling import Application, Request

web = Application()

@web.get("/hello/{name}")
def hello(req: Request) -> str:
    return f"<p>Hello, {req.route_params['name']}</p>"
```

(Server wiring comes in a later commit.)

---

## Commit 4 — Jinja integration

**Implement**

- Optional `template_dir` on construction; lazy or eager Jinja2 environment with sensible autoescape.
- `render(template_name, **context) -> Response`.
- A template filter equivalent to today’s `**unwrap`** so signal-like objects with `.value` render in templates without leaking objects into HTML.

**Test**

- Temporary directory with a tiny template; render with a `signals.signal` and assert output.

**Suggested message:** `feat(kindling): Jinja templates and unwrap filter`

### What app authors can do now

```python
from pathlib import Path
from signals import signal
from kindling import Application, Request

BASE = Path(__file__).resolve().parent
web = Application(template_dir=str(BASE / "templates"))

@web.get("/")
def home(_req: Request):
    n = signal(42)
    return web.render("page.html", n=n)
```

(`page.html` uses `{{ n|unwrap }}`.)

---

## Commit 5 — Security headers and config

**Implement**

- Small **config** object (defaults for security headers, body size limits, optional `Server` header).
- **Finalize** every outgoing response with defaults unless the handler already set those headers.

**Test**

- Dispatch a handler that returns minimal response; assert `X-Content-Type-Options`, etc., are present.

**Suggested message:** `feat(kindling): security defaults on responses`

### What app authors can do now

They pass `config=...` into `Application` if they need to tune limits or headers; defaults work without code changes in the app.

---

## Commit 6 — HTTP/1 parsing and threaded dev server

**Implement**

- Read a single HTTP request from a socket (use `h11` or equivalent), respect `max_request_body_bytes`, build **Request**, write **Response** bytes.
- **Blocking threaded** TCP server that calls `app.dispatch` per connection.

**Test**

- In-process: open a client socket to the server, send a minimal GET, read response (or use a thin helper). Keep the test fast and local.

**Suggested message:** `feat(kindling): HTTP parse and threaded serve()`

### What app authors can do now

```python
from kindling import Application, serve

web = Application(template_dir="templates")

# ... register routes ...

if __name__ == "__main__":
    serve(web, host="127.0.0.1", port=8000)
```

They can hit `http://127.0.0.1:8000/...` in a browser.

---

## Commit 7 — WSGI entrypoint

**Implement**

- `make_wsgi_app(application)` (or `app.wsgi_app`) building a WSGI callable: map environ → Request, dispatch, return iterable body.
- Document that **streaming responses** are out of scope for this adapter until handled explicitly.

**Test**

- Synthetic WSGI environ for GET and POST; assert status and body through the adapter.

**Suggested message:** `feat(kindling): WSGI adapter for production servers`

### What app authors can do now

```python
# myapp.py
web = Application(...)
wsgi_app = web.wsgi_app  # or make_wsgi_app(web)
```

Deploy with **waitress / gunicorn** using `--call myapp:wsgi_app`.

---

## Commit 8 — Live page: same-URL GET and POST + full HTML round-trip

**Implement**

- **LivePage** (or same concept under another name): one path, GET renders a template with injected page helper, POST runs an action then re-renders.
- Legacy **named action** POST field (e.g. `action=`) for the first version.

**Test**

- POST with `action=bump` updates server-side state and next GET/POST response body reflects it (template uses `unwrap`).

**Suggested message:** `feat(kindling): LivePage GET/POST and named actions`

### What app authors can do now

```python
from signals import signal
from kindling import Application, LivePage

web = Application(template_dir="templates")
count = signal(0)
page = LivePage(web, "/", "index.html", context=lambda: {"count": count})

@page.action
def bump():
    count.value += 1
```

Template includes whatever markup represents the count and a control that POSTs the action name the framework expects.

---

## Commit 9 — Browser runtime script and `mount_live_client`

**Implement**

- A small **vanilla JS** payload (string or static file) that: parses a binding manifest from the document, delegates clicks/submits, POSTs back to the same URL, **morphs** returned HTML into `document.body`.
- Route `GET /_kindling/client.js` (or your chosen prefix) registered once per app.
- Ensure **LivePage** construction **mounts** that route idempotently.

**Test**

- GET the client URL returns 200 and JavaScript content type.
- LivePage still passes existing POST/morph tests if you add headless checks later; for this commit, server-side tests suffice.

**Suggested message:** `feat(kindling): morph client script and auto-mount`

### What app authors can do now

In the HTML layout:

```html
<script src="/_kindling/client.js" defer></script>
{% if kindling_live is defined %}{{ kindling_live.binding_tag()|safe }}{% endif %}
```

(Use the actual helper name your framework injects.)

They use **LivePage** + actions; the browser updates without full navigation.

---

## Commit 10 — Element `id` handlers (`@page["btn"].onclick`)

**Implement**

- **ElementRef** / event binder: register `(element_id, event_name)` → handler; POST carries target id + event (hidden fields or convention you document).
- **Binding manifest** embedded as JSON for the client script.
- Handlers with **no parameters** vs **Request** parameter, matching current Stoke behavior.

**Test**

- POST simulating `target=id&event=click` runs handler and re-render shows new state.
- Unknown binding → 400.

**Suggested message:** `feat(kindling): LivePage element id bindings`

### What app authors can do now

```python
@page["inc"].onclick
def inc():
    count.value += 1

@page["note-form"].onsubmit
def add_line(req: Request):
    text = req.form_value("body") or ""
    if text:
        lines.value = [*lines.value, text[:280]]
```

Templates use matching `id="inc"` and `id="note-form"`.

---

## Commit 11 — Reactive scope: `Application.reactive` context manager

**Implement**

- Context manager `**with web.reactive(name, path=..., template=...):`** that sets a **contextvar** scope, rejects nesting on the same task/thread, and on successful exit registers routes + manifest the same way as LivePage.
- **Duplicate path / duplicate scope name** validation.

**Test**

- Nested `with web.reactive` raises.
- Two scopes same path or same name raise.
- `signal()` / `computed()` from `**kindling`** outside the block raise with a clear message.

**Suggested message:** `feat(kindling): reactive scope context manager`

### What app authors can do now

```python
from kindling import Application, signal

web = Application(template_dir="templates")

with web.reactive("main", path="/", template="index.html"):
    count = signal(0)
```

(Decorators `@bind` / `@on` come in the next commit.)

---

## Commit 12 — `@bind`, `@live`, `@on` and scoped primitives

**Implement**

- `**signal` / `computed`** wrappers that require the active reactive scope; `**effect`** re-exported from `signals` without scope.
- Decorators `**bind(selector, mode)`**, `**live(key)**`, `**on(element_id, event)**` registering into the scope; **Python syntax note**: use second positional for bind mode (`"text"`, `"html"`, `"json"`) because `as` is not a keyword argument name.
- On scope exit: merge `@on` handlers into LivePage seed bindings; build **computed** nodes for bind/live bodies for the push pipeline.

**Test**

- Full flow: `@on` click increments signal; response HTML updates.
- `@bind` participates in snapshot (next commit may wire SSE; for now ensure computed runs and template GET works).

**Suggested message:** `feat(kindling): bind, live, on and scoped signal/computed`

### What app authors can do now

```python
from kindling import Application, Request, signal
from kindling.reactive import bind, on

web = Application(template_dir="templates")

with web.reactive("app", path="/", template="index.html"):
    count = signal(0)
    lines = signal[list[str]]([])

    @bind("#count-readout", "text")
    def count_text():
        return str(count.value)

    @bind("#board", "html")
    def board():
        return "<ul>" + "".join(f"<li>{t}</li>" for t in lines.value) + "</ul>"

    @on("inc-btn", "click")
    def inc():
        count.value += 1

    @on("note-form", "submit")
    def add(req: Request):
        t = req.form_value("body") or ""
        if t:
            lines.value = [*lines.value, t[:280]]
```

Template: SSR first paint with `{{ count|unwrap }}`, matching `id`s for bind/on.

---

## Commit 13 — SSE fanout for arbitrary snapshots (`@web.sse`)

**Implement**

- **SseFanout**: subscribe `signals.effect` to a snapshot callable; on change, encode JSON and push to all connected EventSource clients; ping on idle.
- `**@web.sse("/stream")`** decorator registering GET handler returning streaming response.

**Test**

- Snapshot depends on a signal; effect runs; connect handler returns stream (unit-level: consume first chunk or mock queue).

**Suggested message:** `feat(kindling): SSE helper and @app.sse decorator`

### What app authors can do now

```python
from signals import effect, signal
from kindling import Application

web = Application(template_dir="templates")
board_html = signal("<ul></ul>")

@web.sse("/stream")
def snapshot():
    return {"html": board_html.value}
```

Browser: `new EventSource("/stream")` and apply `data` to the DOM in their own script (framework does not need to own that UI).

---

## Commit 14 — Reactive transport: bind/live over SSE

**Implement**

- When a reactive scope registers **at least one** `@bind` or `@live`, register `**GET /_kindling/reactive/{scope_name}`** (name URL-safe) and embed a second JSON blob in `**binding_tag()`** with the stream URL.
- Extend the **client script** to open **EventSource**, parse payloads, apply **text / html / json** to `querySelector(selector)`, merge `**@live`** payloads into a documented global or `CustomEvent`.

**Test**

- GET reactive stream returns 200 and `text/event-stream`.
- First event payload includes bind/live keys (parse first SSE line in test).

**Suggested message:** `feat(kindling): reactive SSE and client apply`

### What app authors can do now

No new API — the same `@bind` / `@live` from commit 12; after this commit, open tabs receive **incremental** updates without POST when signals change, while POST still works for actions.

---

## Commit 15 — Developer ergonomics

**Implement**

- `**Application.run(host=..., port=..., label=..., quiet=...)`** printing a URL and calling `serve`.
- `**app.wsgi_app`** lazy property mirroring `make_wsgi_app`.
- Optional **duplicate-route strict mode** if you added it in the plan.

**Test**

- `wsgi_app` is stable across repeated access.
- (Optional) smoke: `run` with a flag to avoid binding a real port in CI.

**Suggested message:** `feat(kindling): run() and wsgi_app convenience`

### What app authors can do now

```python
if __name__ == "__main__":
    web.run(host="127.0.0.1", port=5050, label="My app —")
```

---

## Commit 16 — Documentation and rename pass

**Implement**

- **README** / **ARCHITECTURE** (or **KINDLING.md**): product name, install, user quickstart, WSGI vs dev server + SSE caveats.
- Replace string prefixes (`_stoke`, `stoke_`, etc.) consistently with `**kindling`** in public URLs and JSON `id`s where authors see them.
- **REACTIVE_RFC** equivalent updated for Kindling naming and bind syntax.

**Test**

- Docs-only commit; run full test suite once.

**Suggested message:** `docs: Kindling naming and author guide`

### What app authors can do now

They follow public docs; URLs and script paths match the released name.

---

## Appendix — Order of dependency (for reviewers)


| Commit | Depends on     |
| ------ | -------------- |
| 1      | —              |
| 2      | 1              |
| 3      | 2              |
| 4      | 3 + `signals`  |
| 5      | 3              |
| 6      | 3, 5           |
| 7      | 3, 5           |
| 8      | 4, 6           |
| 9      | 8              |
| 10     | 9              |
| 11     | 10             |
| 12     | 11 + `signals` |
| 13     | 4 + `signals`  |
| 14     | 12, 9, 13      |
| 15     | 7, 6           |
| 16     | 14             |


---

## Appendix — What this guide intentionally omits

- Internal function/class listings and algorithms.
- **signals** internals (already shipped).
- Optional future work: ASGI, strict duplicate routes, explicit reactive `exports=` for template context, split wheel vs `signals`.

A programmer clearing **all non-signals code** and following commits **1 → 16** with tests green after each step will reproduce the framework behavior described in your RFC/plan under the **Kindling** name.