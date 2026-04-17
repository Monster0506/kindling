import json
from pathlib import Path

from kindling import Application, Request, bind, expose, signal
from kindling.streaming import StreamedHttpResponse


def test_reactive_stream_get_returns_sse_with_bind_payload(tmp_path: Path):
    tpl = tmp_path / "index.html"
    tpl.write_text("<span id='x'>0</span>", encoding="utf-8")
    app = Application(template_dir=str(tmp_path))

    @app.reactive("app", path="/", template="index.html")
    def _():
        count = signal(7)
        expose(count=count)

        @bind("#x", "text")
        def readout() -> str:
            return str(count.value)

    r = app.dispatch(Request.build("GET", "/_kindling/reactive/app"))
    assert isinstance(r, StreamedHttpResponse)
    ct = {k.lower(): v for k, v in r.headers}["content-type"]
    assert "event-stream" in ct
    line = next(r.iterator).decode()
    assert line.startswith("data:")
    payload = json.loads(line.split("data:", 1)[1].strip())
    assert payload["binds"]["#x"]["value"] == "7"
