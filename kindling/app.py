from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from kindling.config import KindlingConfig, finalize_response, finalize_streaming
from kindling.request import Request
from kindling.response import Response, html_response
from kindling.streaming import StreamedHttpResponse

if TYPE_CHECKING:
    pass


def _unwrap_filter(value: object) -> object:
    v = getattr(value, "value", value)
    return v

Handler = Callable[[Request], object]


@dataclass
class _Route:
    methods: frozenset[str]
    pattern_segments: tuple[str | None, ...]  # None = {param}
    param_names: tuple[str, ...]
    handler: Handler


def _split_path(path: str) -> list[str]:
    p = path.strip("/")
    if not p:
        return []
    return [seg for seg in p.split("/") if seg]


def _compile_pattern(pattern: str) -> tuple[tuple[str | None, ...], tuple[str, ...]]:
    segs = _split_path(pattern)
    out: list[str | None] = []
    names: list[str] = []
    for s in segs:
        if s.startswith("{") and s.endswith("}"):
            name = s[1:-1]
            if not name:
                raise ValueError(f"empty param in pattern {pattern!r}")
            out.append(None)
            names.append(name)
        else:
            out.append(s)
    return (tuple(out), tuple(names))


def _match_route(
    route: _Route, path_segments: list[str]
) -> dict[str, str] | None:
    if len(path_segments) != len(route.pattern_segments):
        return None
    params: dict[str, str] = {}
    pi = 0
    for i, pat in enumerate(route.pattern_segments):
        actual = path_segments[i]
        if pat is None:
            params[route.param_names[pi]] = actual
            pi += 1
        elif pat != actual:
            return None
    return params


def _normalize_handler_result(result: object) -> Response | StreamedHttpResponse:
    if isinstance(result, StreamedHttpResponse):
        return result
    if isinstance(result, Response):
        return result
    if isinstance(result, str):
        return html_response(result)
    if isinstance(result, bytes):
        return Response(
            status=200,
            headers=(
                ("Content-Type", "application/octet-stream"),
                ("Content-Length", str(len(result))),
            ),
            body=result,
        )
    raise TypeError(
        f"handler must return Response, StreamedHttpResponse, str, or bytes; got {type(result)!r}"
    )


@dataclass
class Application:
    template_dir: str | None = None
    config: KindlingConfig = field(default_factory=KindlingConfig)
    _routes: list[_Route] = field(default_factory=list, repr=False)
    _jinja_env: Environment | None = field(default=None, init=False, repr=False)
    _reactive_names: set[str] = field(default_factory=set, repr=False)
    _reactive_paths: set[str] = field(default_factory=set, repr=False)
    _reactive_scopes: dict[str, object] = field(default_factory=dict, repr=False)
    _wsgi_app_holder: object | None = field(default=None, init=False, repr=False)

    def _ensure_jinja(self) -> Environment:
        if self._jinja_env is not None:
            return self._jinja_env
        if not self.template_dir:
            raise RuntimeError("Application(template_dir=...) is required to render templates")
        env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )
        env.filters["unwrap"] = _unwrap_filter
        self._jinja_env = env
        return env

    def render_to_html(self, template_name: str, **context: object) -> str:
        tpl = self._ensure_jinja().get_template(template_name)
        return tpl.render(**context)

    def render(self, template_name: str, **context: object) -> Response:
        return html_response(self.render_to_html(template_name, **context))

    def route(
        self,
        pattern: str,
        methods: Iterable[str],
        handler: Handler,
    ) -> None:
        mset = frozenset(m.upper() for m in methods)
        segs, names = _compile_pattern(pattern)
        self._routes.append(_Route(methods=mset, pattern_segments=segs, param_names=names, handler=handler))

    def get(self, pattern: str) -> Callable[[Handler], Handler]:
        def deco(fn: Handler) -> Handler:
            self.route(pattern, ("GET",), fn)
            return fn

        return deco

    def post(self, pattern: str) -> Callable[[Handler], Handler]:
        def deco(fn: Handler) -> Handler:
            self.route(pattern, ("POST",), fn)
            return fn

        return deco

    def page(self, pattern: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a :class:`~kindling.live_page.LivePage` from an HTML callable (no ``reactive`` block).

        The handler may take ``()``, ``(req)``, or ``(req, kindling_live)`` and return ``str`` or
        :class:`~kindling.response.Response`. String bodies get ``kindling-live-config`` and
        ``/_kindling/client.js`` injected before ``</body>`` when missing (same as Jinja LivePage
        templates and ``@body`` inside ``app.reactive``).
        """

        def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
            from kindling.live_page import LivePage

            LivePage(self, pattern, None, context=lambda: {}, html_body=fn)
            return fn

        return deco

    def reactive(self, name: str, *, path: str, template: str | None = None):
        from kindling.reactive import managed_scope

        return managed_scope(self, name, path, template)

    def sse(self, pattern: str):
        from kindling.sse import register_sse_route

        def deco(fn: Callable[[], dict]) -> Callable[[], dict]:
            register_sse_route(self, pattern, fn)
            return fn

        return deco

    @property
    def wsgi_app(self) -> object:
        if self._wsgi_app_holder is None:
            from kindling.wsgi import make_wsgi_app

            self._wsgi_app_holder = make_wsgi_app(self)
        return self._wsgi_app_holder

    def run(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        *,
        label: str = "",
        quiet: bool = False,
    ) -> None:
        from kindling.server import serve

        if not quiet:
            print(f"{label or 'Serving'} http://{host}:{port}/")
        serve(self, host=host, port=port)

    def dispatch(self, req: Request) -> Response | StreamedHttpResponse:
        path_segs = _split_path(req.path)
        for r in self._routes:
            if req.method not in r.methods:
                continue
            params = _match_route(r, path_segs)
            if params is None:
                continue
            merged = Request.build(
                req.method,
                req.path,
                query_string=req.query_string,
                headers=req.headers,
                body=req.body,
                route_params=params,
            )
            out = _normalize_handler_result(r.handler(merged))
            if isinstance(out, StreamedHttpResponse):
                return finalize_streaming(out, self.config)
            return finalize_response(out, self.config)
        from kindling.response import not_found

        return finalize_response(not_found(), self.config)
