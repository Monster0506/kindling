from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path

from kindling.request import Request
from kindling.response import Response, not_found

_MIME_TYPES: dict[str, str] = {
    ".css":   "text/css; charset=utf-8",
    ".js":    "application/javascript; charset=utf-8",
    ".mjs":   "application/javascript; charset=utf-8",
    ".html":  "text/html; charset=utf-8",
    ".htm":   "text/html; charset=utf-8",
    ".json":  "application/json",
    ".svg":   "image/svg+xml",
    ".ico":   "image/x-icon",
    ".png":   "image/png",
    ".jpg":   "image/jpeg",
    ".jpeg":  "image/jpeg",
    ".gif":   "image/gif",
    ".webp":  "image/webp",
    ".woff":  "font/woff",
    ".woff2": "font/woff2",
    ".ttf":   "font/ttf",
    ".otf":   "font/otf",
    ".txt":   "text/plain; charset=utf-8",
    ".xml":   "application/xml",
    ".pdf":   "application/pdf",
}


def _mime_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in _MIME_TYPES:
        return _MIME_TYPES[suffix]
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "application/octet-stream"


@dataclass(frozen=True, slots=True)
class _StaticMount:
    url_prefix: str
    fs_root: Path


def serve_static(mount: _StaticMount, req: Request) -> Response:
    rel = req.path[len(mount.url_prefix):].lstrip("/")

    if not rel:
        return not_found()

    parts = rel.split("/")
    if any(p in ("", ".", "..") for p in parts):
        return not_found()

    candidate = mount.fs_root / rel

    try:
        resolved = candidate.resolve()
        fs_root_resolved = mount.fs_root.resolve()
    except OSError:
        return not_found()

    if not resolved.is_relative_to(fs_root_resolved):
        return not_found()

    if not resolved.is_file():
        return not_found()

    try:
        data = resolved.read_bytes()
    except OSError:
        return not_found()

    return Response(
        status=200,
        headers=(
            ("Content-Type", _mime_for(resolved)),
            ("Content-Length", str(len(data))),
        ),
        body=data,
    )
