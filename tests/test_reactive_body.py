from pathlib import Path

import pytest

from kindling import Application, Request, body, expose, signal
from kindling.live_page import LivePage


def test_reactive_body_returns_html():
    app = Application()

    @app.reactive("p", path="/p")
    def _():
        @body
        def page(_req: Request) -> str:
            return "<!DOCTYPE html><html><body>hi</body></html>"

    r = app.dispatch(Request.build("GET", "/p"))
    assert r.status == 200
    assert b"hi" in r.body
    assert b"kindling-live-config" in r.body
    assert b"_kindling/client.js" in r.body


def test_reactive_requires_template_or_body():
    app = Application()
    with pytest.raises(ValueError, match="needs template="):

        @app.reactive("n", path="/n")
        def _():
            pass


def test_body_rejects_when_template_set(tmp_path: Path):
    app = Application(template_dir=str(tmp_path))
    (tmp_path / "t.html").write_text("<p>x</p>", encoding="utf-8")
    with pytest.raises(ValueError, match="Cannot use body"):

        @app.reactive("z", path="/z", template="t.html")
        def _():
            @body
            def _c() -> str:
                return "<html></html>"


def test_expose_module_level(tmp_path: Path):
    app = Application(template_dir=str(tmp_path))
    (tmp_path / "t.html").write_text("<p>{{ n|unwrap }}</p>", encoding="utf-8")

    @app.reactive("e", path="/", template="t.html")
    def _():
        n = signal(3)
        expose(n=n)

    r = app.dispatch(Request.build("GET", "/"))
    assert b"3" in r.body


def test_livepage_xor_template_and_body():
    app = Application()
    with pytest.raises(ValueError, match="exactly one"):
        LivePage(app, "/", None, context=lambda: {}, html_body=None)
    with pytest.raises(ValueError, match="exactly one"):
        LivePage(
            app,
            "/",
            "a.html",
            context=lambda: {},
            html_body=lambda _r: "<p>x</p>",
        )
