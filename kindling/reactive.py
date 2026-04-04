from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Callable, Iterator, TypeVar
from urllib.parse import quote

from signals import computed as _computed
from signals import effect
from signals import signal as _signal

if TYPE_CHECKING:
    from kindling.app import Application

T = TypeVar("T")

_reactive_scope: ContextVar[ReactiveScope | None] = ContextVar(
    "kindling_reactive_scope", default=None
)


class ReactiveScope:
    """Active `with app.reactive(...)` scope; collects bind/live/on and template exports."""

    def __init__(self, app: Application, name: str, path: str, template: str) -> None:
        self.app = app
        self.name = name
        self.path = path
        self.template = template
        self._exports: dict[str, Any] = {}
        self._on_handlers: dict[tuple[str, str], Callable[..., object]] = {}
        self._binds: list[tuple[str, str, Any]] = []
        self._lives: list[tuple[str, Any]] = []

    def expose(self, **variables: Any) -> None:
        """Expose names to the Jinja template (e.g. ``expose(count=count)``)."""
        self._exports.update(variables)

    def template_context(self) -> dict[str, Any]:
        return dict(self._exports)


def signal(initial: T) -> Any:
    if _reactive_scope.get() is None:
        raise RuntimeError("kindling.signal() requires an active reactive scope (use `with app.reactive(...):`)")
    return _signal(initial)


def computed(fn: Any) -> Any:
    if _reactive_scope.get() is None:
        raise RuntimeError("kindling.computed() requires an active reactive scope (use `with app.reactive(...):`)")
    return _computed(fn)


def bind(selector: str, mode: str):
    if mode not in ("text", "html", "json"):
        raise ValueError("bind mode must be 'text', 'html', or 'json'")

    def deco(fn: Any) -> Any:
        sc = _reactive_scope.get()
        if sc is None:
            raise RuntimeError("bind() requires an active reactive scope")
        cell = _computed(fn)
        sc._binds.append((selector, mode, cell))
        return fn

    return deco


def live(key: str):
    def deco(fn: Any) -> Any:
        sc = _reactive_scope.get()
        if sc is None:
            raise RuntimeError("live() requires an active reactive scope")
        cell = _computed(fn)
        sc._lives.append((key, cell))
        return fn

    return deco


def on(element_id: str, event: str):
    def deco(fn: Any) -> Any:
        sc = _reactive_scope.get()
        if sc is None:
            raise RuntimeError("on() requires an active reactive scope")
        sc._on_handlers[(element_id, event.lower())] = fn
        return fn

    return deco


def reactive_sse_snapshot(scope: ReactiveScope) -> dict[str, object]:
    binds = {sel: {"mode": mode, "value": cell.value} for sel, mode, cell in scope._binds}
    live = {key: cell.value for key, cell in scope._lives}
    return {"binds": binds, "live": live}


__all__ = [
    "ReactiveScope",
    "bind",
    "computed",
    "effect",
    "live",
    "managed_scope",
    "on",
    "signal",
]


@contextmanager
def managed_scope(app: Application, name: str, path: str, template: str) -> Iterator[ReactiveScope]:
    if _reactive_scope.get() is not None:
        raise RuntimeError("Nested kindling.reactive scope is not allowed")
    if name in app._reactive_names:
        raise ValueError(f"Duplicate reactive scope name: {name!r}")
    if path in app._reactive_paths:
        raise ValueError(f"Duplicate reactive path: {path!r}")
    scope = ReactiveScope(app, name, path, template)
    token = _reactive_scope.set(scope)
    try:
        yield scope
    except BaseException:
        _reactive_scope.reset(token)
        raise
    _reactive_scope.reset(token)
    app._reactive_names.add(name)
    app._reactive_paths.add(path)
    app._reactive_scopes[name] = scope
    from kindling.live_page import LivePage
    from kindling.sse import register_sse_route

    reactive_url: str | None = None
    if scope._binds or scope._lives:
        safe = quote(scope.name, safe="")
        reactive_url = f"/_kindling/reactive/{safe}"
        register_sse_route(app, reactive_url, lambda sc=scope: reactive_sse_snapshot(sc))

    LivePage(
        app,
        path,
        template,
        context=scope.template_context,
        seed_element_handlers=dict(scope._on_handlers),
        reactive_stream_url=reactive_url,
    )
