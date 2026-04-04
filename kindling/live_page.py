from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

from kindling.request import Request
from kindling.response import Response, not_found

if TYPE_CHECKING:
    from kindling.app import Application

ContextFn = Callable[[], Mapping[str, Any]]
ActionFn = Callable[..., object]


class KindlingLiveHelper:
    """Injected into templates as `kindling_live`; binding tag added in later commits."""

    def binding_tag(self) -> str:
        return ""


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
        self._helper = KindlingLiveHelper()
        app.route(path, ("GET",), self._on_get)
        app.route(path, ("POST",), self._on_post)

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
        name = req.form_value("action")
        if not name:
            return not_found()
        fn = self._actions.get(name)
        if fn is None:
            return not_found()
        self._call_action(fn, req)
        return self._render(req)
