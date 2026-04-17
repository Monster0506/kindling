from __future__ import annotations

import inspect
import uuid
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

from kindling.client_js import KINDLING_CLIENT_PATH, mount_kindling_client
from kindling.request import Request
from kindling.response import Response, bad_request, html_response, not_found

if TYPE_CHECKING:
    from kindling.app import Application
    from kindling.reactive import ConnectionScope, ReactiveScopeMeta

ContextFn = Callable[[], Mapping[str, Any]]
ActionFn = Callable[..., object]


class KindlingLiveHelper:
    def __init__(
        self,
        page: LivePage,
        conn_id: str | None = None,
        scope: ConnectionScope | None = None,
    ) -> None:
        self._page = page
        self._conn_id = conn_id
        self._scope = scope

    def binding_tag(self) -> str:
        import json

        cfg = self._page._binding_manifest(conn_id=self._conn_id, scope=self._scope)
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
        scope_meta: ReactiveScopeMeta | None = None,
    ) -> None:
        # When scope_meta is set, template/html_body come from the per-connection scope.
        # For direct LivePage usage (no scope_meta), exactly one of template_name/html_body is required.
        if scope_meta is None and (template_name is None) == (html_body is None):
            raise ValueError("LivePage requires exactly one of template_name (str) or html_body=")
        self._app = app
        self._path = path
        self._template_name = template_name
        self._html_body = html_body
        self._context = context
        self._reactive_stream_url = reactive_stream_url
        self._scope_meta = scope_meta
        self._actions: dict[str, ActionFn] = {}
        self._element_handlers: dict[tuple[str, str], ActionFn] = {}
        if seed_element_handlers:
            self._element_handlers.update(seed_element_handlers)
        mount_kindling_client(app)
        app.route(path, ("GET",), self._on_get)
        app.route(path, ("POST",), self._on_post)

    def __getitem__(self, element_id: str) -> ElementBinder:
        return ElementBinder(self, element_id)

    def _register_element(self, element_id: str, event: str, fn: ActionFn) -> None:
        self._element_handlers[(element_id, event.lower())] = fn

    def _binding_manifest(
        self,
        conn_id: str | None = None,
        scope: ConnectionScope | None = None,
    ) -> dict[str, Any]:
        bindings: dict[str, list[str]] = {}
        handlers = scope._on_handlers if scope is not None else self._element_handlers
        for (eid, ev), _ in handlers.items():
            bindings.setdefault(eid, []).append(ev)
        cfg: dict[str, Any] = {"kindling": 1, "path": self._path, "bindings": bindings}
        if self._reactive_stream_url:
            cfg["reactiveUrl"] = self._reactive_stream_url
        if conn_id is not None:
            cfg["conn"] = conn_id
        return cfg

    def action(self, fn: ActionFn) -> ActionFn:
        self._actions[fn.__name__] = fn
        return fn

    def _call_action(self, fn: ActionFn, req: Request) -> object:
        sig = inspect.signature(fn)
        if len(sig.parameters) == 0:
            return fn()
        return fn(req)

    def _invoke_html_body(
        self,
        fn: Callable[..., object],
        req: Request,
        helper: KindlingLiveHelper,
    ) -> object:
        sig = inspect.signature(fn)
        n = len(sig.parameters)
        if n == 0:
            return fn()
        if n == 1:
            return fn(req)
        if n == 2:
            return fn(req, helper)
        raise TypeError(f"body handler must take 0-2 arguments, not {n}")

    def _maybe_inject_kindling_runtime(self, html: str, helper: KindlingLiveHelper) -> str:
        parts: list[str] = []
        if "kindling-live-config" not in html:
            parts.append(helper.binding_tag())
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

    def _render(
        self,
        req: Request,
        conn_id: str | None = None,
        scope: ConnectionScope | None = None,
    ) -> Response:
        helper = KindlingLiveHelper(self, conn_id=conn_id, scope=scope)

        if scope is not None:
            # Per-connection scope rendering
            if scope._html_body is not None:
                out = self._invoke_html_body(scope._html_body, req, helper)
                if isinstance(out, Response):
                    return out
                if isinstance(out, str):
                    return html_response(self._maybe_inject_kindling_runtime(out, helper))
                raise TypeError(
                    f"body handler must return str or Response, got {type(out)!r}"
                )
            ctx = dict(scope.template_context())
            ctx["kindling_live"] = helper
            assert self._scope_meta is not None
            html = self._app.render_to_html(self._scope_meta.template, **ctx)
            return html_response(self._maybe_inject_kindling_runtime(html, helper))

        # Direct LivePage usage (no scope_meta)
        if self._html_body is not None:
            out = self._invoke_html_body(self._html_body, req, helper)
            if isinstance(out, Response):
                return out
            if isinstance(out, str):
                return html_response(self._maybe_inject_kindling_runtime(out, helper))
            raise TypeError(
                f"body handler must return str or Response, got {type(out)!r}"
            )
        ctx = dict(self._context())
        ctx["kindling_live"] = helper
        assert self._template_name is not None
        html = self._app.render_to_html(self._template_name, **ctx)
        return html_response(self._maybe_inject_kindling_runtime(html, helper))

    def _on_get(self, req: Request) -> Response:
        if self._scope_meta is not None:
            conn_id = str(uuid.uuid4())
            scope = self._scope_meta.create_conn(conn_id)
            return self._render(req, conn_id=conn_id, scope=scope)
        return self._render(req)

    def _on_post(self, req: Request) -> Response:
        if self._scope_meta is not None:
            conn_id = req.form_value("kindling_conn")
            scope = self._scope_meta.get_conn(conn_id) if conn_id else None
            if scope is None:
                conn_id = conn_id or str(uuid.uuid4())
                scope = self._scope_meta.create_conn(conn_id)

            target = req.form_value("kindling_target")
            ev = (req.form_value("kindling_event") or "").lower()
            if target and ev:
                fn = scope._on_handlers.get((target, ev))
                if fn is None:
                    return bad_request("Unknown binding")
                self._call_action(fn, req)
                return self._render(req, conn_id=conn_id, scope=scope)

            name = req.form_value("action")
            if not name:
                return not_found()
            fn = self._actions.get(name)
            if fn is None:
                return not_found()
            self._call_action(fn, req)
            return self._render(req, conn_id=conn_id, scope=scope)

        # Direct LivePage usage (no scope_meta)
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
