from pathlib import Path

from signals import signal

from kindling import Application, Request
from kindling.live_page import LivePage


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
