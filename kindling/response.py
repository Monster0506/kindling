from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Response:
    status: int
    headers: tuple[tuple[str, str], ...]
    body: bytes

    @classmethod
    def build(
        cls,
        status: int = 200,
        *,
        headers: tuple[tuple[str, str], ...] | None = None,
        body: bytes = b"",
    ) -> Response:
        return cls(status=status, headers=headers or (), body=body)


def text_response(content: str, status: int = 200) -> Response:
    data = content.encode("utf-8")
    h = (("Content-Type", "text/plain; charset=utf-8"), ("Content-Length", str(len(data))))
    return Response(status=status, headers=h, body=data)


def html_response(content: str, status: int = 200) -> Response:
    data = content.encode("utf-8")
    h = (("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(data))))
    return Response(status=status, headers=h, body=data)


def json_response(obj: object, status: int = 200) -> Response:
    data = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    h = (("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(data))))
    return Response(status=status, headers=h, body=data)


def not_found(message: str = "Not Found") -> Response:
    return text_response(message, status=404)


def bad_request(message: str = "Bad Request") -> Response:
    return text_response(message, status=400)


def internal_server_error(message: str = "Internal Server Error") -> Response:
    return text_response(message, status=500)
