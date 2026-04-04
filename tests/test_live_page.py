from pathlib import Path

from signals import signal

from kindling import Application, Request
from kindling.live_page import LivePage


def test_live_page_html_body_auto_injects_runtime():
    app = Application()
    LivePage(
        app,
        "/raw",
        None,
        context=lambda: {},
        html_body=lambda: "<html><body><p>ok</p></body></html>",
    )
    r = app.dispatch(Request.build("GET", "/raw"))
    assert r.status == 200
    assert b"<p>ok</p>" in r.body
    assert b"kindling-live-config" in r.body
    assert b"_kindling/client.js" in r.body


def test_live_page_html_body_skips_inject_when_present():
    app = Application()
    LivePage(
        app,
        "/raw",
        None,
        context=lambda: {},
        html_body=lambda: (
            '<html><body>x<script type="application/json" id="kindling-live-config">{}</script>'
            '<script src="/_kindling/client.js" defer></script></body></html>'
        ),
    )
    r = app.dispatch(Request.build("GET", "/raw"))
    assert r.body.count(b"kindling-live-config") == 1
    assert r.body.count(b"_kindling/client.js") == 1


def test_application_page_registers_livepage():
    app = Application()

    @app.page("/greet")
    def greet() -> str:
        return "<html><body><p>hello</p></body></html>"

    r = app.dispatch(Request.build("GET", "/greet"))
    assert r.status == 200
    assert b"hello" in r.body
    assert b"kindling-live-config" in r.body


def test_live_page_get_post_roundtrip(tmp_path: Path):
    tpl = tmp_path / "index.html"
    tpl.write_text("<p id='c'>{{ count|unwrap }}</p>", encoding="utf-8")

    app = Application(template_dir=str(tmp_path))
    count = signal(0)
    page = LivePage(app, "/", "index.html", context=lambda: {"count": count})

    @page.action
    def bump() -> None:
        count.value += 1

    r0 = app.dispatch(Request.build("GET", "/"))
    assert r0.status == 200
    assert b">0<" in r0.body or b"0</p>" in r0.body

    r1 = app.dispatch(
        Request.build(
            "POST",
            "/",
            headers=(("Content-Type", "application/x-www-form-urlencoded"),),
            body=b"action=bump",
        )
    )
    assert r1.status == 200
    assert b"1" in r1.body
