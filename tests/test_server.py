import re
import socket
import threading
import time
from pathlib import Path

from kindling import Application, Request, bind, expose, serve, signal


def _read_http_response(sock: socket.socket) -> bytes:
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buf += chunk
    head, _, rest = buf.partition(b"\r\n\r\n")
    m = re.search(rb"content-length:\s*(\d+)", head.lower())
    if not m:
        return buf
    need = int(m.group(1))
    body = rest
    while len(body) < need:
        chunk = sock.recv(4096)
        if not chunk:
            break
        body += chunk
    return head + b"\r\n\r\n" + body


def test_threaded_server_get():
    app = Application()

    @app.get("/ping")
    def ping(_req: Request) -> str:
        return "ok"

    ports: list[int] = []
    th = threading.Thread(
        target=lambda: serve(app, host="127.0.0.1", port=0, bind_port_out=ports),
        daemon=True,
    )
    th.start()
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline and not ports:
        time.sleep(0.01)
    assert ports, "server did not bind"
    port = ports[0]

    c = socket.create_connection(("127.0.0.1", port), timeout=5)
    try:
        c.sendall(b"GET /ping HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
        data = _read_http_response(c)
    finally:
        c.close()

    assert b"200" in data
    assert data.endswith(b"ok")


def test_threaded_server_streams_reactive_sse(tmp_path: Path):
    tpl = tmp_path / "i.html"
    tpl.write_text('<p id="x">0</p>', encoding="utf-8")
    app = Application(template_dir=str(tmp_path))
    @app.reactive("st", path="/", template="i.html")
    def _():
        n = signal(0)
        expose(n=n)

        @bind("#x", "text")
        def readout() -> str:
            return str(n.value)

    ports: list[int] = []
    th = threading.Thread(
        target=lambda: serve(app, host="127.0.0.1", port=0, bind_port_out=ports),
        daemon=True,
    )
    th.start()
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline and not ports:
        time.sleep(0.01)
    assert ports, "server did not bind"
    port = ports[0]

    c = socket.create_connection(("127.0.0.1", port), timeout=5)
    try:
        c.sendall(
            b"GET /_kindling/reactive/st HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
        )
        c.settimeout(3.0)
        buf = b""
        while b"data:" not in buf and len(buf) < 128_000:
            try:
                part = c.recv(8192)
            except TimeoutError:
                break
            if not part:
                break
            buf += part
    finally:
        c.close()

    assert b"200" in buf
    assert b"text/event-stream" in buf.lower()
    assert b"data:" in buf
