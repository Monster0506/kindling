from pathlib import Path

from signals import signal

from kindling import Application, Request
from kindling.client_js import KINDLING_CLIENT_PATH
from kindling.live_page import LivePage


def test_client_js_route_returns_javascript(tmp_path: Path):
    app = Application(template_dir=str(tmp_path))
    (tmp_path / "i.html").write_text("x", encoding="utf-8")
    n = signal(0)
    LivePage(app, "/", "i.html", context=lambda: {"n": n})

    r = app.dispatch(Request.build("GET", KINDLING_CLIENT_PATH))
    assert r.status == 200
    ct = {k.lower(): v for k, v in r.headers}["content-type"]
    assert "javascript" in ct
    assert b"Idiomorph" in r.body
    assert b"fetch" in r.body
