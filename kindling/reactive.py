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

    def __init__(self, app: Application, name: str, path: str, template: str | None) -> None:
        self.app = app
        self.name = name
        self.path = path
        self.template = template
        self._exports: dict[str, Any] = {}
        self._on_handlers: dict[tuple[str, str], Callable[..., object]] = {}
        self._binds: list[tuple[str, str, Any]] = []
        self._lives: list[tuple[str, Any]] = []
        self._html_body: Callable[..., object] | None = None

    def body(self, fn: Callable[..., object]) -> Callable[..., object]:
        """Register raw HTML (same as module-level :func:`body` inside ``with app.reactive``)."""
        if self._html_body is not None:
            raise ValueError("Only one body handler is allowed per reactive scope")
        if self.template is not None:
            raise ValueError("Cannot use body() when template= is set")
        self._html_body = fn
        return fn

    def expose(self, **variables: Any) -> None:
        """Expose names to Jinja (same as module-level :func:`expose` inside the block)."""
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


def expose(**variables: Any) -> None:
    """Merge names into the Jinja context for the current ``app.reactive`` block."""
    sc = _reactive_scope.get()
    if sc is None:
        raise RuntimeError("expose() requires an active reactive scope (use `with app.reactive(...):`)")
    sc.expose(**variables)


def body(fn: Callable[..., object]) -> Callable[..., object]:
    """Register raw HTML for the current reactive block (no ``template=``).

    Same as ``scope.body`` but does not require ``as scope``. The handler may take
    ``()``, ``(req)``, or ``(req, kindling_live)`` and must return ``str`` or ``Response``.
    """
    sc = _reactive_scope.get()
    if sc is None:
        raise RuntimeError("body() requires an active reactive scope (use `with app.reactive(...):`)")
    return sc.body(fn)


def reactive_sse_snapshot(scope: ReactiveScope) -> dict[str, object]:
    binds = {sel: {"mode": mode, "value": cell.value} for sel, mode, cell in scope._binds}
    live = {key: cell.value for key, cell in scope._lives}
    return {"binds": binds, "live": live}


__all__ = [
    "ReactiveScope",
    "bind",
    "body",
    "computed",
    "effect",
    "expose",
    "live",
    "managed_scope",
    "on",
    "signal",
]


@contextmanager
def managed_scope(
    app: Application, name: str, path: str, template: str | None = None
) -> Iterator[ReactiveScope]:
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

    if template is not None and scope._html_body is not None:
        raise ValueError("Pass either template= or @body, not both")
    if template is None and scope._html_body is None:
        raise ValueError("reactive() needs template=... or exactly one @body handler")

    reactive_url: str | None = None
    if scope._binds or scope._lives:
        safe = quote(scope.name, safe="")
        reactive_url = f"/_kindling/reactive/{safe}"
        register_sse_route(app, reactive_url, lambda sc=scope: reactive_sse_snapshot(sc))

    LivePage(
        app,
        path,
        template_name=template,
        context=scope.template_context,
        html_body=scope._html_body,
        seed_element_handlers=dict(scope._on_handlers),
        reactive_stream_url=reactive_url,
    )
