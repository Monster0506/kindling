import tempfile
from pathlib import Path

import pytest

from kindling import Application, Request


@pytest.fixture()
def static_dir(tmp_path: Path) -> Path:
    (tmp_path / "style.css").write_bytes(b"body { color: red; }")
    (tmp_path / "app.js").write_bytes(b"console.log('hi');")
    (tmp_path / "data.json").write_bytes(b'{"ok": true}')
    (tmp_path / "image.png").write_bytes(b"\x89PNG")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "nested.txt").write_bytes(b"hello")
    (tmp_path / "unknown.zzunknown").write_bytes(b"data")
    return tmp_path


def make_app(tmp_path: Path) -> Application:
    app = Application()
    app.static("/static", str(tmp_path))
    return app


def test_serves_css(static_dir: Path) -> None:
    app = make_app(static_dir)
    r = app.dispatch(Request.build("GET", "/static/style.css"))
    assert r.status == 200
    assert r.body == b"body { color: red; }"
    assert "text/css" in dict(r.headers).get("Content-Type", "")


def test_serves_js(static_dir: Path) -> None:
    app = make_app(static_dir)
    r = app.dispatch(Request.build("GET", "/static/app.js"))
    assert r.status == 200
    assert "javascript" in dict(r.headers).get("Content-Type", "")


def test_serves_json(static_dir: Path) -> None:
    app = make_app(static_dir)
    r = app.dispatch(Request.build("GET", "/static/data.json"))
    assert r.status == 200
    assert "application/json" in dict(r.headers).get("Content-Type", "")


def test_serves_nested_file(static_dir: Path) -> None:
    app = make_app(static_dir)
    r = app.dispatch(Request.build("GET", "/static/sub/nested.txt"))
    assert r.status == 200
    assert r.body == b"hello"


def test_unknown_extension_octet_stream(static_dir: Path) -> None:
    app = make_app(static_dir)
    r = app.dispatch(Request.build("GET", "/static/unknown.zzunknown"))
    assert r.status == 200
    assert dict(r.headers).get("Content-Type") == "application/octet-stream"


def test_missing_file_returns_404(static_dir: Path) -> None:
    app = make_app(static_dir)
    r = app.dispatch(Request.build("GET", "/static/nope.css"))
    assert r.status == 404


def test_directory_request_returns_404(static_dir: Path) -> None:
    app = make_app(static_dir)
    r = app.dispatch(Request.build("GET", "/static/sub"))
    assert r.status == 404


def test_traversal_dotdot_returns_404(static_dir: Path) -> None:
    app = make_app(static_dir)
    r = app.dispatch(Request.build("GET", "/static/../etc/passwd"))
    assert r.status == 404


def test_head_returns_headers_no_body(static_dir: Path) -> None:
    app = make_app(static_dir)
    r = app.dispatch(Request.build("HEAD", "/static/style.css"))
    assert r.status == 200
    assert r.body == b""
    assert dict(r.headers).get("Content-Length") == str(len(b"body { color: red; }"))


def test_post_to_static_path_returns_404(static_dir: Path) -> None:
    app = make_app(static_dir)
    r = app.dispatch(Request.build("POST", "/static/style.css"))
    assert r.status == 404


def test_content_length_header(static_dir: Path) -> None:
    app = make_app(static_dir)
    r = app.dispatch(Request.build("GET", "/static/app.js"))
    assert dict(r.headers).get("Content-Length") == str(len(b"console.log('hi');"))


def test_two_mounts(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "foo.txt").write_bytes(b"from-a")
    (b / "bar.txt").write_bytes(b"from-b")

    app = Application()
    app.static("/a", str(a))
    app.static("/b", str(b))

    assert app.dispatch(Request.build("GET", "/a/foo.txt")).body == b"from-a"
    assert app.dispatch(Request.build("GET", "/b/bar.txt")).body == b"from-b"


def test_static_raises_for_nonexistent_dir() -> None:
    app = Application()
    with pytest.raises(ValueError, match="not a directory"):
        app.static("/static", "/nonexistent/path/xyz")


def test_dynamic_route_not_shadowed_by_static(static_dir: Path) -> None:
    # Dynamic routes registered after static mounts lose to the static mount
    # for paths under the same prefix — document this behavior.
    app = make_app(static_dir)

    @app.get("/other/route")
    def handler(_req: Request) -> str:
        return "dynamic"

    r = app.dispatch(Request.build("GET", "/other/route"))
    assert r.status == 200
    assert b"dynamic" in r.body
