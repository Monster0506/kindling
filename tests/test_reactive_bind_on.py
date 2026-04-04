from pathlib import Path

from kindling import Application, Request, bind, on, signal


def test_reactive_on_click_updates_template(tmp_path: Path):
    tpl = tmp_path / "index.html"
    tpl.write_text(
        "<button id='inc-btn'>+</button><p id='c'>{{ count|unwrap }}</p>",
        encoding="utf-8",
    )
    app = Application(template_dir=str(tmp_path))
    with app.reactive("app", path="/", template="index.html") as scope:
        count = signal(0)
        scope.expose(count=count)

        @on("inc-btn", "click")
        def inc() -> None:
            count.value += 1

    r0 = app.dispatch(Request.build("GET", "/"))
    assert b"0" in r0.body
    r1 = app.dispatch(
        Request.build(
            "POST",
            "/",
            headers=(("Content-Type", "application/x-www-form-urlencoded"),),
            body=b"kindling_target=inc-btn&kindling_event=click",
        )
    )
    assert r1.status == 200
    assert b"1" in r1.body


def test_bind_computed_runs(tmp_path: Path):
    tpl = tmp_path / "p.html"
    tpl.write_text("<span id='count-readout'>{{ count|unwrap }}</span>", encoding="utf-8")
    app = Application(template_dir=str(tmp_path))
    with app.reactive("x", path="/page", template="p.html") as scope:
        count = signal(2)
        scope.expose(count=count)

        @bind("#count-readout", "text")
        def count_text() -> str:
            return str(count.value)

    r = app.dispatch(Request.build("GET", "/page"))
    assert r.status == 200
    assert b"2" in r.body
    sc = app._reactive_scopes["x"]  # type: ignore[index]
    assert len(sc._binds) == 1
    _, _, cell = sc._binds[0]
    assert cell.value == "2"
