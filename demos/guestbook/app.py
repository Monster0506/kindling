from __future__ import annotations

import html
from pathlib import Path

from kindling import Application, Request, bind, expose, on, signal


def main() -> None:
    base = Path(__file__).resolve().parent
    app = Application(template_dir=str(base / "templates"))

    @app.reactive("guestbook", path="/", template="index.html")
    def _guestbook() -> None:
        entries = signal(list[str]())

        expose(entries=entries)

        @bind("#entries", "html")
        def entries_html() -> str:
            rows = "".join(f"<li>{html.escape(e)}</li>" for e in entries.value)
            return f"<ul>{rows}</ul>" if rows else "<p class='empty'>No messages yet.</p>"

        @on("add-form", "submit")
        def add_entry(req: Request) -> None:
            text = (req.form_value("message") or "").strip()
            if not text:
                return
            cur = list(entries.value)
            cur.append(text)
            entries.value = cur

    app.run(host="127.0.0.1", port=8002, label="Guestbook demo -")


if __name__ == "__main__":
    main()
