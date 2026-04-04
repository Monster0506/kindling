import io

from kindling import Application, Request
from kindling.wsgi import make_wsgi_app


def test_wsgi_get():
    app = Application()

    @app.get("/hi")
    def hi(_req: Request) -> str:
        return "hello"

    wsgi = make_wsgi_app(app)
    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/hi",
        "QUERY_STRING": "",
        "wsgi.input": io.BytesIO(b""),
    }
    captured: list[tuple[str, list[tuple[str, str]]]] = []

    def start_response(status: str, headers: list[tuple[str, str]], exc_info=None) -> None:
        captured.append((status, headers))

    body = b"".join(wsgi(environ, start_response))  # type: ignore[arg-type]
    assert captured
    assert captured[0][0].startswith("200")
    assert body == b"hello"


def test_wsgi_post_form():
    app = Application()

    @app.post("/save")
    def save(req: Request) -> str:
        return req.form_value("a") or ""

    wsgi = make_wsgi_app(app)
    raw = b"a=one"
    environ = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": "/save",
        "QUERY_STRING": "",
        "CONTENT_TYPE": "application/x-www-form-urlencoded",
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": io.BytesIO(raw),
    }
    captured: list[tuple[str, list[tuple[str, str]]]] = []

    def start_response(status: str, headers: list[tuple[str, str]], exc_info=None) -> None:
        captured.append((status, headers))

    body = b"".join(wsgi(environ, start_response))  # type: ignore[arg-type]
    assert body == b"one"
