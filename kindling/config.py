from __future__ import annotations

from dataclasses import dataclass

from kindling.response import Response


@dataclass
class KindlingConfig:
    """Defaults for security headers, limits, and optional Server."""

    max_request_body_bytes: int = 1024 * 1024
    server_header: str | None = None
    default_security_headers: tuple[tuple[str, str], ...] = (
        ("X-Content-Type-Options", "nosniff"),
        ("X-Frame-Options", "DENY"),
        ("Referrer-Policy", "strict-origin-when-cross-origin"),
        ("Permissions-Policy", "geolocation=(), microphone=(), camera=()"),
    )


def finalize_response(resp: Response, config: KindlingConfig) -> Response:
    """Apply config defaults for headers not already set by the handler."""
    present = {name.lower() for name, _ in resp.headers}
    prefix: list[tuple[str, str]] = []
    if config.server_header and "server" not in present:
        prefix.append(("Server", config.server_header))
    for name, value in config.default_security_headers:
        if name.lower() not in present:
            prefix.append((name, value))
    if not prefix:
        return resp
    return Response(status=resp.status, headers=tuple(prefix) + resp.headers, body=resp.body)
