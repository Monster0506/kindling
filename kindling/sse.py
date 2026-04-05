from __future__ import annotations

import json
import queue
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING

from signals import effect

from kindling.request import Request
from kindling.streaming import StreamedHttpResponse

if TYPE_CHECKING:
    from kindling.app import Application

SnapshotFn = Callable[[], dict]


class SseFanout:
    def __init__(self, snapshot: SnapshotFn) -> None:
        self._snapshot = snapshot
        self._queues: list[queue.SimpleQueue[str]] = []
        effect(self._broadcast)

    def _broadcast(self) -> None:
        payload = json.dumps(self._snapshot())
        for q in list(self._queues):
            q.put_nowait(payload)

    def stream(self) -> Iterator[bytes]:
        q: queue.SimpleQueue[str] = queue.SimpleQueue()
        self._queues.append(q)
        try:
            yield f"data: {json.dumps(self._snapshot())}\n\n".encode()
            while True:
                try:
                    msg = q.get(timeout=20.0)
                except queue.Empty:
                    yield b": ping\n\n"
                    continue
                yield f"data: {msg}\n\n".encode()
        finally:
            self._queues.remove(q)


def register_sse_route(app: Application, pattern: str, snapshot: SnapshotFn) -> SseFanout:
    fan = SseFanout(snapshot)

    @app.get(pattern)
    def _sse_handler(_req: Request) -> StreamedHttpResponse:
        headers = (
            ("Content-Type", "text/event-stream; charset=utf-8"),
            ("Cache-Control", "no-cache"),
            ("Connection", "keep-alive"),
            ("X-Accel-Buffering", "no"),
        )
        return StreamedHttpResponse(200, headers, fan.stream())

    return fan
