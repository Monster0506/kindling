from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

from kindling.client_js import mount_kindling_client
from kindling.request import Request
from kindling.response import Response, bad_request, not_found

if TYPE_CHECKING:
    from kindling.app import Application

ContextFn = Callable[[], Mapping[str, Any]]
ActionFn = Callable[..., object]


class KindlingLiveHelper:
    """Injected into templates as `kindling_live`; embeds config JSON for the client script."""

    def __init__(self, page: LivePage) -> None:
        self._page = page

    def binding_tag(self) -> str:
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
    """One path: GET renders a template; POST runs a named `action` then re-renders."""

    def __init__(
        self,
        app: Application,
        path: str,
        template_name: str,
        context: ContextFn,
    ) -> None:
        self._app = app
        self._path = path
        self._template_name = template_name
        self._context = context
        self._actions: dict[str, ActionFn] = {}
        self._element_handlers: dict[tuple[str, str], ActionFn] = {}
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
        return {"kindling": 1, "path": self._path, "bindings": bindings}

    def action(self, fn: ActionFn) -> ActionFn:
        self._actions[fn.__name__] = fn
        return fn

    def _call_action(self, fn: ActionFn, req: Request) -> object:
        sig = inspect.signature(fn)
        if len(sig.parameters) == 0:
            return fn()
        return fn(req)

    def _render(self, req: Request) -> Response:
        ctx = dict(self._context())
        ctx["kindling_live"] = self._helper
        return self._app.render(self._template_name, **ctx)

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
