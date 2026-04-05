from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from kindling.request import Request

if TYPE_CHECKING:
    from kindling.app import Application

WSGIApp = Callable[..., object]


def _environ_to_headers(environ: dict[str, str]) -> tuple[tuple[str, str], ...]:
    out: list[tuple[str, str]] = []
    if ct := environ.get("CONTENT_TYPE"):
        out.append(("Content-Type", ct))
    if cl := environ.get("CONTENT_LENGTH"):
        out.append(("Content-Length", cl))
    for key, value in environ.items():
        if key.startswith("HTTP_"):
            name = "-".join(part.title() for part in key[5:].split("_"))
            out.append((name, value))
    return tuple(out)


def make_wsgi_app(app: Application) -> WSGIApp:
    def wsgi_app(environ: dict, start_response: Callable) -> list[bytes]:
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO") or "/"
        query = environ.get("QUERY_STRING") or ""
        headers = _environ_to_headers({k: str(v) for k, v in environ.items()})
        length = int(environ.get("CONTENT_LENGTH") or 0)
        body = environ["wsgi.input"].read(length) if length else b""
        req = Request.build(method, path, query_string=query, headers=headers, body=body)
        resp = app.dispatch(req)
        status_text = {
            200: "OK",
            404: "Not Found",
            500: "Internal Server Error",
        }.get(resp.status, "OK")
        status = f"{resp.status} {status_text}"
        header_list = list(resp.headers)
        start_response(status, header_list)
        return [resp.body]

    return wsgi_app
