from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Iterator, TypeVar

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
    """Active `with app.reactive(...)` scope; extended in later commits for bind/live/on."""

    def __init__(self, app: Application, name: str, path: str, template: str) -> None:
        self.app = app
        self.name = name
        self.path = path
        self.template = template

    def template_context(self) -> dict[str, Any]:
        return {}


def signal(initial: T) -> Any:
    if _reactive_scope.get() is None:
        raise RuntimeError("kindling.signal() requires an active reactive scope (use `with app.reactive(...):`)")
    return _signal(initial)


def computed(fn: Any) -> Any:
    if _reactive_scope.get() is None:
        raise RuntimeError("kindling.computed() requires an active reactive scope (use `with app.reactive(...):`)")
    return _computed(fn)


__all__ = ["ReactiveScope", "computed", "effect", "managed_scope", "signal"]


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
    from kindling.live_page import LivePage

    LivePage(app, path, template, context=scope.template_context)
