from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, select_autoescape

from kindling.config import KindlingConfig, finalize_response
from kindling.request import Request
from kindling.response import Response, html_response

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


def _normalize_handler_result(result: object) -> Response:
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
    raise TypeError(f"handler must return Response, str, or bytes; got {type(result)!r}")


@dataclass
class Application:
    template_dir: str | None = None
    config: KindlingConfig = field(default_factory=KindlingConfig)
    _routes: list[_Route] = field(default_factory=list, repr=False)
    _jinja_env: Environment | None = field(default=None, init=False, repr=False)
    _reactive_names: set[str] = field(default_factory=set, repr=False)
    _reactive_paths: set[str] = field(default_factory=set, repr=False)

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

    def render(self, template_name: str, **context: object) -> Response:
        tpl = self._ensure_jinja().get_template(template_name)
        html = tpl.render(**context)
        return html_response(html)

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

    def reactive(self, name: str, *, path: str, template: str):
        from kindling.reactive import managed_scope

        return managed_scope(self, name, path, template)

    def dispatch(self, req: Request) -> Response:
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
            return finalize_response(out, self.config)
        from kindling.response import not_found

        return finalize_response(not_found(), self.config)
