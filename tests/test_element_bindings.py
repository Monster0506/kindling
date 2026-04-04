from pathlib import Path

from signals import signal

from kindling import Application, Request
from kindling.live_page import LivePage


def test_element_click_updates_state(tmp_path: Path):
    tpl = tmp_path / "index.html"
    tpl.write_text("<p id='c'>{{ count|unwrap }}</p>", encoding="utf-8")

    app = Application(template_dir=str(tmp_path))
    count = signal(0)
    page = LivePage(app, "/", "index.html", context=lambda: {"count": count})

    @page["inc"].onclick
    def inc() -> None:
        count.value += 1

    body = b"kindling_target=inc&kindling_event=click"
    r = app.dispatch(
        Request.build(
            "POST",
            "/",
            headers=(("Content-Type", "application/x-www-form-urlencoded"),),
            body=body,
        )
    )
    assert r.status == 200
    assert b"1" in r.body


def test_unknown_element_binding_is_400(tmp_path: Path):
    tpl = tmp_path / "x.html"
    tpl.write_text("ok", encoding="utf-8")
    app = Application(template_dir=str(tmp_path))
    n = signal(0)
    LivePage(app, "/", "x.html", context=lambda: {"n": n})

    r = app.dispatch(
        Request.build(
            "POST",
            "/",
            headers=(("Content-Type", "application/x-www-form-urlencoded"),),
            body=b"kindling_target=nope&kindling_event=click",
        )
    )
    assert r.status == 400
