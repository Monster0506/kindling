from signals import signal

from kindling import Application, Request
from kindling.streaming import StreamedHttpResponse


def test_sse_fanout_pushes_on_signal_change():
    from kindling.sse import SseFanout

    s = signal(1)
    fan = SseFanout(lambda: {"n": s.value})
    it = fan.stream()
    first = next(it)
    assert b"data:" in first
    assert b"1" in first
    s.value = 2
    second = next(it)
    assert b"2" in second


def test_app_sse_dispatch_returns_event_stream():
    app = Application()
    board = signal("<ul></ul>")

    @app.sse("/stream")
    def snapshot():
        return {"html": board.value}

    out = app.dispatch(Request.build("GET", "/stream"))
    assert isinstance(out, StreamedHttpResponse)
    assert out.status == 200
    ct = {k.lower(): v for k, v in out.headers}["content-type"]
    assert "event-stream" in ct
    chunk = next(out.iterator)
    assert b"data:" in chunk
    assert b"<ul></ul>" in chunk
