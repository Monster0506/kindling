---
sidebar_position: 1
---

# Introduction

**Kindling** is a small Python web layer built on the **[signals](https://github.com/monster0506/pysignals)** package (`signal`, `computed`, `effect`). In this repository, **signals** is included as a **git submodule** at `signals/` (see `.gitmodules`); `uv` installs it from that tree for development. It gives you:

- **Routing** with `@app.get` / `@app.post`, path parameters like `/hello/{name}`, and `Request.route_params`.
- **Jinja** rendering via `Application(template_dir=...)` and `render` / `render_to_html`.
- **Live pages** (`LivePage`): one URL for GET + POST, optional browser **morph** after POST and **SSE** for reactive fragments.
- **Reactive scopes** (`with app.reactive(...):`) with `signal`, `bind`, `live`, `on`, and `expose` for server-driven UI updates.

Use `app.run()` for a threaded dev server, or `serve()` / `make_wsgi_app()` for programmatic serving and WSGI.

## When to use Kindling

Kindling fits **small apps**, **demos**, and **experiments** where you want Python-first HTML, minimal dependencies (h11, Jinja2, signals), and optional live DOM sync without a separate frontend build.

For large production systems, you may still use Kindling for prototypes or internal tools; review [Deployment](./getting-started#wsgi-and-streaming) notes on WSGI and streaming.

## Next steps

- [Getting started](./getting-started) - install, hello world, run tests
- [Routing](./routing) - patterns, handlers, responses
- [Live pages](./live-pages) - GET/POST, actions, element bindings
- [Reactive UI](./reactive-ui) - signals, bind, live, SSE
