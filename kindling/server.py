from __future__ import annotations

import socket
import threading
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import h11

from kindling.config import finalize_response
from kindling.request import Request
from kindling.response import Response
from kindling.streaming import StreamedHttpResponse

if TYPE_CHECKING:
    from kindling.app import Application


def _handle_client(sock: socket.socket, app: Application) -> None:
    conn = h11.Connection(h11.SERVER)
    method = ""
    path = "/"
    query = ""
    headers_list: list[tuple[str, str]] = []
    body = bytearray()
    try:
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                return
            conn.receive_data(chunk)
            while True:
                event = conn.next_event()
                if event is h11.NEED_DATA:
                    break
                if isinstance(event, h11.Request):
                    method = event.method.decode("ascii", errors="replace").upper()
                    target = event.target.decode("ascii", errors="replace")
                    parsed = urlparse(target)
                    path = parsed.path or "/"
                    query = parsed.query or ""
                    headers_list = [
                        (k.decode("latin-1", errors="replace"), v.decode("latin-1", errors="replace"))
                        for k, v in event.headers
                    ]
                elif isinstance(event, h11.Data):
                    body.extend(event.data)
                    if len(body) > app.config.max_request_body_bytes:
                        err = finalize_response(
                            Response(
                                status=413,
                                headers=(("Content-Type", "text/plain; charset=utf-8"),),
                                body=b"Payload Too Large",
                            ),
                            app.config,
                        )
                        _write_response_raw(sock, conn, err)
                        return
                elif isinstance(event, h11.EndOfMessage):
                    req = Request.build(
                        method,
                        path,
                        query_string=query,
                        headers=tuple(headers_list),
                        body=bytes(body),
                    )
                    resp = app.dispatch(req)
                    _write_response_raw(sock, conn, resp)
                    return
                elif isinstance(event, h11.ConnectionClosed):
                    return
    finally:
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        sock.close()


def _write_response_raw(
    sock: socket.socket,
    conn: h11.Connection,
    resp: Response | StreamedHttpResponse,
) -> None:
    if isinstance(resp, StreamedHttpResponse):
        _write_streamed_response_raw(sock, conn, resp)
        return
    header_list = [(k.encode("latin-1"), v.encode("latin-1")) for k, v in resp.headers]
    sock.sendall(conn.send(h11.Response(status_code=resp.status, headers=header_list)))
    if resp.body:
        sock.sendall(conn.send(h11.Data(data=resp.body)))
    sock.sendall(conn.send(h11.EndOfMessage()))


def _write_streamed_response_raw(
    sock: socket.socket, conn: h11.Connection, resp: StreamedHttpResponse
) -> None:
    headers = list(resp.headers)
    names = {k.lower() for k, _ in headers}
    if "content-length" not in names and "transfer-encoding" not in names:
        headers = [("Transfer-Encoding", "chunked")] + headers
    header_list = [(k.encode("latin-1"), v.encode("latin-1")) for k, v in headers]
    sock.sendall(conn.send(h11.Response(status_code=resp.status, headers=header_list)))
    try:
        for chunk in resp.iterator:
            if chunk:
                sock.sendall(conn.send(h11.Data(data=chunk)))
    finally:
        sock.sendall(conn.send(h11.EndOfMessage()))


def serve(
    app: Application,
    host: str = "127.0.0.1",
    port: int = 8000,
    *,
    bind_port_out: list[int] | None = None,
) -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    if bind_port_out is not None:
        bind_port_out.append(srv.getsockname()[1])
    srv.listen(128)
    try:
        while True:
            client, _ = srv.accept()
            t = threading.Thread(target=_handle_client, args=(client, app), daemon=True)
            t.start()
    finally:
        srv.close()
