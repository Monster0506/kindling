import re
from pathlib import Path

from kindling import Application, Request, bind, expose, on, signal


def test_reactive_on_click_updates_template(tmp_path: Path):
    tpl = tmp_path / "index.html"
    tpl.write_text(
        "<button id='inc-btn'>+</button><p id='c'>{{ count|unwrap }}</p>",
        encoding="utf-8",
    )
    app = Application(template_dir=str(tmp_path))

    @app.reactive("app", path="/", template="index.html")
    def _():
        count = signal(0)
        expose(count=count)

        @on("inc-btn", "click")
        def inc() -> None:
            count.value += 1

    r0 = app.dispatch(Request.build("GET", "/"))
    assert b"0" in r0.body
    assert b"kindling-live-config" in r0.body
    assert b"_kindling/client.js" in r0.body

    m = re.search(rb'"conn"\s*:\s*"([^"]+)"', r0.body)
    assert m, "conn_id missing from GET response"
    conn_id = m.group(1).decode()

    r1 = app.dispatch(
        Request.build(
            "POST",
            "/",
            headers=(("Content-Type", "application/x-www-form-urlencoded"),),
            body=f"kindling_target=inc-btn&kindling_event=click&kindling_conn={conn_id}".encode(),
        )
    )
    assert r1.status == 200
    assert b"1" in r1.body


def test_bind_computed_runs(tmp_path: Path):
    tpl = tmp_path / "p.html"
    tpl.write_text("<span id='count-readout'>{{ count|unwrap }}</span>", encoding="utf-8")
    app = Application(template_dir=str(tmp_path))

    @app.reactive("x", path="/page", template="p.html")
    def _():
        count = signal(2)
        expose(count=count)

        @bind("#count-readout", "text")
        def count_text() -> str:
            return str(count.value)

    r = app.dispatch(Request.build("GET", "/page"))
    assert r.status == 200
    assert b"2" in r.body
    # Verify a connection scope was created with the bind
    meta = app._reactive_scopes["x"]
    assert len(meta._registry) == 1
    conn_scope = next(iter(meta._registry.values()))
    assert len(conn_scope._binds) == 1
    _, _, cell = conn_scope._binds[0]
    assert cell.value == "2"
