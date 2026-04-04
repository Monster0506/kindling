from __future__ import annotations

from collections.abc import Iterator


class StreamedHttpResponse:
    """Response with a byte iterator body (e.g. SSE). Not fully supported by the dev server or WSGI adapter yet."""

    __slots__ = ("status", "headers", "iterator")

    def __init__(
        self,
        status: int,
        headers: tuple[tuple[str, str], ...],
        iterator: Iterator[bytes],
    ) -> None:
        self.status = status
        self.headers = headers
        self.iterator = iterator
