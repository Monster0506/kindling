from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

from kindling.client_js import KINDLING_CLIENT_PATH, mount_kindling_client
from kindling.request import Request
from kindling.response import Response, bad_request, html_response, not_found

if TYPE_CHECKING:
    from kindling.app import Application

ContextFn = Callable[[], Mapping[str, Any]]
ActionFn = Callable[..., object]


class KindlingLiveHelper:
    """Injected into templates as `kindling_live`; embeds config JSON for the client script."""

    def __init__(self, page: LivePage) -> None:
        self._page = page

    def binding_tag(self) -> str:
        """Return the ``<script type="application/json" id="kindling-live-config">`` element.

        LivePage injects this and the client ``<script>`` before ``</body>`` for both Jinja
        templates and ``html_body`` strings when missing. Call this in a template only if you
        need a custom placement.
        """
        import json

        cfg = self._page._binding_manifest()
        return (
            f'<script type="application/json" id="kindling-live-config">'
            f"{json.dumps(cfg)}"
            f"</script>"
        )


class ElementBinder:
    def __init__(self, page: LivePage, element_id: str) -> None:
        self._page = page
        self._element_id = element_id

    def onclick(self, fn: ActionFn) -> ActionFn:
        self._page._register_element(self._element_id, "click", fn)
        return fn

    def onsubmit(self, fn: ActionFn) -> ActionFn:
        self._page._register_element(self._element_id, "submit", fn)
        return fn


class LivePage:
    """One path: GET renders a template or a ``body`` callable; POST then re-renders."""

    def __init__(
        self,
        app: Application,
        path: str,
        template_name: str | None,
        context: ContextFn,
        *,
        html_body: Callable[..., object] | None = None,
        seed_element_handlers: dict[tuple[str, str], ActionFn] | None = None,
        reactive_stream_url: str | None = None,
    ) -> None:
        if (template_name is None) == (html_body is None):
            raise ValueError("LivePage requires exactly one of template_name (str) or html_body=")
        self._app = app
        self._path = path
        self._template_name = template_name
        self._html_body = html_body
        self._context = context
        self._reactive_stream_url = reactive_stream_url
        self._actions: dict[str, ActionFn] = {}
        self._element_handlers: dict[tuple[str, str], ActionFn] = {}
        if seed_element_handlers:
            self._element_handlers.update(seed_element_handlers)
        self._helper = KindlingLiveHelper(self)
        mount_kindling_client(app)
        app.route(path, ("GET",), self._on_get)
        app.route(path, ("POST",), self._on_post)

    def __getitem__(self, element_id: str) -> ElementBinder:
        return ElementBinder(self, element_id)

    def _register_element(self, element_id: str, event: str, fn: ActionFn) -> None:
        self._element_handlers[(element_id, event.lower())] = fn

    def _binding_manifest(self) -> dict[str, Any]:
        bindings: dict[str, list[str]] = {}
        for (eid, ev), _ in self._element_handlers.items():
            bindings.setdefault(eid, []).append(ev)
        cfg: dict[str, Any] = {"kindling": 1, "path": self._path, "bindings": bindings}
        if self._reactive_stream_url:
            cfg["reactiveUrl"] = self._reactive_stream_url
        return cfg

    def action(self, fn: ActionFn) -> ActionFn:
        self._actions[fn.__name__] = fn
        return fn

    def _call_action(self, fn: ActionFn, req: Request) -> object:
        sig = inspect.signature(fn)
        if len(sig.parameters) == 0:
            return fn()
        return fn(req)

    def _invoke_html_body(self, req: Request) -> object:
        assert self._html_body is not None
        fn = self._html_body
        sig = inspect.signature(fn)
        n = len(sig.parameters)
        if n == 0:
            return fn()
        if n == 1:
            return fn(req)
        if n == 2:
            return fn(req, self._helper)
        raise TypeError(f"body handler must take 0–2 arguments, not {n}")

    def _maybe_inject_kindling_runtime(self, html: str) -> str:
        """Insert live config + client script before ``</body>`` if the HTML omits them."""
        parts: list[str] = []
        if "kindling-live-config" not in html:
            parts.append(self._helper.binding_tag())
        if "_kindling/client.js" not in html:
            parts.append(f'<script src="{KINDLING_CLIENT_PATH}" defer></script>')
        if not parts:
            return html
        blob = "".join(parts)
        lower = html.lower()
        close = lower.rfind("</body>")
        if close != -1:
            return html[:close] + blob + html[close:]
        return html + blob

    def _render(self, req: Request) -> Response:
        if self._html_body is not None:
            out = self._invoke_html_body(req)
            if isinstance(out, Response):
                return out
            if isinstance(out, str):
                return html_response(self._maybe_inject_kindling_runtime(out))
            raise TypeError(f"body handler must return str or Response, got {type(out)!r}")
        ctx = dict(self._context())
        ctx["kindling_live"] = self._helper
        assert self._template_name is not None
        html = self._app.render_to_html(self._template_name, **ctx)
        return html_response(self._maybe_inject_kindling_runtime(html))

    def _on_get(self, req: Request) -> Response:
        return self._render(req)

    def _on_post(self, req: Request) -> Response:
        target = req.form_value("kindling_target")
        ev = (req.form_value("kindling_event") or "").lower()
        if target and ev:
            fn = self._element_handlers.get((target, ev))
            if fn is None:
                return bad_request("Unknown binding")
            self._call_action(fn, req)
            return self._render(req)

        name = req.form_value("action")
        if not name:
            return not_found()
        fn = self._actions.get(name)
        if fn is None:
            return not_found()
        self._call_action(fn, req)
        return self._render(req)
