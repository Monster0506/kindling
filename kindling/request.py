from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import parse_qs, unquote_plus


def _parse_form_urlencoded(body: bytes) -> dict[str, list[str]]:
    if not body:
        return {}
    text = body.decode("utf-8", errors="replace")
    pairs: dict[str, list[str]] = {}
    for part in text.split("&"):
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
        else:
            k, v = part, ""
        key = unquote_plus(k.replace("+", " "))
        val = unquote_plus(v.replace("+", " "))
        pairs.setdefault(key, []).append(val)
    return pairs


@dataclass(frozen=True, slots=True)
class Request:
    """HTTP request (immutable)."""

    method: str
    path: str
    query_string: str
    headers: tuple[tuple[str, str], ...]
    body: bytes
    route_params: Mapping[str, str]

    @classmethod
    def build(
        cls,
        method: str,
        path: str,
        *,
        query_string: str = "",
        headers: tuple[tuple[str, str], ...] | None = None,
        body: bytes = b"",
        route_params: Mapping[str, str] | None = None,
    ) -> Request:
        return cls(
            method=method.upper(),
            path=path,
            query_string=query_string,
            headers=headers or (),
            body=body,
            route_params=route_params or {},
        )

    def header(self, name: str, default: str | None = None) -> str | None:
        want = name.lower()
        for k, v in self.headers:
            if k.lower() == want:
                return v
        return default

    @property
    def form(self) -> dict[str, list[str]]:
        ct = (self.header("content-type", "") or "").split(";")[0].strip().lower()
        if ct != "application/x-www-form-urlencoded":
            return {}
        return _parse_form_urlencoded(self.body)

    def form_value(self, name: str, default: str | None = None) -> str | None:
        vals = self.form.get(name)
        if not vals:
            return default
        return vals[0]

    def query(self, name: str, default: str | None = None) -> str | None:
        if not self.query_string:
            return default
        q = parse_qs(self.query_string, keep_blank_values=True)
        vals = q.get(name)
        if not vals:
            return default
        return vals[0]

    def json_body(self) -> object:
        return json.loads(self.body.decode("utf-8"))
