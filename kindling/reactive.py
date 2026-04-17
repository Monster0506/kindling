from __future__ import annotations

import json
import queue
import threading
import uuid
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Callable, Iterator, TypeVar

from signals import computed as _computed
from signals import effect
from signals import signal as _signal

if TYPE_CHECKING:
    from kindling.app import Application

T = TypeVar("T")

_reactive_scope: ContextVar[ConnectionScope | None] = ContextVar(
    "kindling_reactive_scope", default=None
)


class ConnectionScope:
    """Per-connection reactive state. Created fresh for each browser connection."""

    def __init__(self, meta: ReactiveScopeMeta) -> None:
        self._meta = meta
        self._exports: dict[str, Any] = {}
        self._on_handlers: dict[tuple[str, str], Callable[..., object]] = {}
        self._binds: list[tuple[str, str, Any]] = []
        self._lives: list[tuple[str, Any]] = []
        self._html_body: Callable[..., object] | None = None
        self._sse_q: queue.SimpleQueue | None = None
        self._sse_effect: object = None  # hold reference to prevent GC

    def expose(self, **variables: Any) -> None:
        self._exports.update(variables)

    def template_context(self) -> dict[str, Any]:
        return dict(self._exports)

    def _init_effect(self) -> None:
        if not self._binds and not self._lives:
            return

        @effect
        def _sse_effect() -> None:
            payload = json.dumps(_scope_snapshot(self))
            q = self._sse_q
            if q is not None:
                q.put_nowait(payload)

        self._sse_effect = _sse_effect


class ReactiveScopeMeta:
    """Registered once at startup. Factory is called per connection."""

    def __init__(
        self,
        app: Application,
        name: str,
        path: str,
        template: str | None,
        factory_fn: Callable[[], None],
    ) -> None:
        self.app = app
        self.name = name
        self.path = path
        self.template = template
        self.factory_fn = factory_fn
        self._registry: dict[str, ConnectionScope] = {}
        self._lock = threading.Lock()

    def create_conn(self, conn_id: str) -> ConnectionScope:
        scope = ConnectionScope(self)
        token = _reactive_scope.set(scope)
        try:
            self.factory_fn()
        finally:
            _reactive_scope.reset(token)
        scope._init_effect()
        with self._lock:
            self._registry[conn_id] = scope
        return scope

    def get_conn(self, conn_id: str) -> ConnectionScope | None:
        return self._registry.get(conn_id)

    def remove_conn(self, conn_id: str) -> None:
        with self._lock:
            self._registry.pop(conn_id, None)


def _scope_snapshot(scope: ConnectionScope) -> dict[str, object]:
    binds = {sel: {"mode": mode, "value": cell.value} for sel, mode, cell in scope._binds}
    live = {key: cell.value for key, cell in scope._lives}
    return {"binds": binds, "live": live}


def per_connection_sse_stream(
    meta: ReactiveScopeMeta,
    conn_id: str,
    scope: ConnectionScope,
) -> Iterator[bytes]:
    q: queue.SimpleQueue[str] = queue.SimpleQueue()
    scope._sse_q = q
    try:
        snapshot = json.dumps(_scope_snapshot(scope))
        yield f"data: {snapshot}\n\n".encode()
        while True:
            try:
                msg = q.get(timeout=20.0)
                yield f"data: {msg}\n\n".encode()
            except queue.Empty:
                yield b": ping\n\n"
    finally:
        scope._sse_q = None
        meta.remove_conn(conn_id)


def signal(initial: T) -> Any:
    if _reactive_scope.get() is None:
        raise RuntimeError(
            "kindling.signal() requires an active reactive scope (use `@app.reactive(...)`)"
        )
    return _signal(initial)


def computed(fn: Any) -> Any:
    if _reactive_scope.get() is None:
        raise RuntimeError(
            "kindling.computed() requires an active reactive scope (use `@app.reactive(...)`)"
        )
    return _computed(fn)


def bind(selector: str, mode: str) -> Callable:
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


def live(key: str) -> Callable:
    def deco(fn: Any) -> Any:
        sc = _reactive_scope.get()
        if sc is None:
            raise RuntimeError("live() requires an active reactive scope")
        cell = _computed(fn)
        sc._lives.append((key, cell))
        return fn

    return deco


def on(element_id: str, event: str) -> Callable:
    def deco(fn: Any) -> Any:
        sc = _reactive_scope.get()
        if sc is None:
            raise RuntimeError("on() requires an active reactive scope")
        sc._on_handlers[(element_id, event.lower())] = fn
        return fn

    return deco


def expose(**variables: Any) -> None:
    sc = _reactive_scope.get()
    if sc is None:
        raise RuntimeError(
            "expose() requires an active reactive scope (use `@app.reactive(...)`)"
        )
    sc.expose(**variables)


def body(fn: Callable[..., object]) -> Callable[..., object]:
    sc = _reactive_scope.get()
    if sc is None:
        raise RuntimeError(
            "body() requires an active reactive scope (use `@app.reactive(...)`)"
        )
    if sc._html_body is not None:
        raise ValueError("Only one body handler is allowed per reactive scope")
    if sc._meta.template is not None:
        raise ValueError("Cannot use body() when template= is set")
    sc._html_body = fn
    return fn


class _ProtoMeta:
    """Minimal stand-in meta for probe runs."""

    def __init__(self, template: str | None) -> None:
        self.template = template


def _probe_factory(
    factory_fn: Callable[[], None], template: str | None
) -> ConnectionScope:
    """Run the factory in a throw-away scope to validate and detect structure."""
    proto = _ProtoMeta(template)
    probe: ConnectionScope = ConnectionScope.__new__(ConnectionScope)
    probe._meta = proto  # type: ignore[assignment]
    probe._exports = {}
    probe._on_handlers = {}
    probe._binds = []
    probe._lives = []
    probe._html_body = None
    probe._sse_q = None
    probe._sse_effect = None

    token = _reactive_scope.set(probe)
    try:
        factory_fn()
    finally:
        _reactive_scope.reset(token)
    return probe


def register_reactive(
    app: Application,
    name: str,
    path: str,
    template: str | None,
    factory_fn: Callable[[], None],
) -> ReactiveScopeMeta:
    if _reactive_scope.get() is not None:
        raise RuntimeError("Cannot register a reactive scope inside a factory function")
    if name in app._reactive_names:
        raise ValueError(f"Duplicate reactive scope name: {name!r}")
    if path in app._reactive_paths:
        raise ValueError(f"Duplicate reactive path: {path!r}")

    # Probe to validate and detect whether streams are needed
    probe = _probe_factory(factory_fn, template)
    if template is not None and probe._html_body is not None:
        raise ValueError("Pass either template= or @body, not both")
    if template is None and probe._html_body is None:
        raise ValueError("reactive() needs template=... or exactly one @body handler")

    meta = ReactiveScopeMeta(app, name, path, template, factory_fn)
    app._reactive_names.add(name)
    app._reactive_paths.add(path)
    app._reactive_scopes[name] = meta

    has_streams = bool(probe._binds or probe._lives)
    reactive_url: str | None = None
    if has_streams:
        from urllib.parse import quote

        safe = quote(name, safe="")
        reactive_url = f"/_kindling/reactive/{safe}"
        _register_per_conn_sse_route(app, reactive_url, meta)

    from kindling.live_page import LivePage

    LivePage(
        app,
        path,
        template_name=template,
        context=lambda: {},
        scope_meta=meta,
        reactive_stream_url=reactive_url,
    )

    return meta


def _register_per_conn_sse_route(
    app: Application, pattern: str, meta: ReactiveScopeMeta
) -> None:
    from kindling.request import Request
    from kindling.streaming import StreamedHttpResponse

    @app.get(pattern)
    def _sse_handler(req: Request) -> StreamedHttpResponse:
        conn_id = req.query("conn") or str(uuid.uuid4())
        scope = meta.get_conn(conn_id)
        if scope is None:
            scope = meta.create_conn(conn_id)
        headers = (
            ("Content-Type", "text/event-stream; charset=utf-8"),
            ("Cache-Control", "no-cache"),
            ("Connection", "keep-alive"),
            ("X-Accel-Buffering", "no"),
        )
        return StreamedHttpResponse(
            200, headers, per_connection_sse_stream(meta, conn_id, scope)
        )


__all__ = [
    "ConnectionScope",
    "ReactiveScopeMeta",
    "bind",
    "body",
    "computed",
    "effect",
    "expose",
    "live",
    "on",
    "register_reactive",
    "signal",
]
