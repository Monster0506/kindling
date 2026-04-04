"""
Demo: @live pushes a payload; the page listens for the kindling-live CustomEvent.
"""

from __future__ import annotations

import time
from pathlib import Path

from kindling import Application, bind, expose, live, on, signal


def main() -> None:
    base = Path(__file__).resolve().parent
    app = Application(template_dir=str(base / "templates"))

    with app.reactive("pulse", path="/", template="index.html"):
        started = time.monotonic()
        tick = signal(0)

        expose(tick=tick)

        @bind("#tick-readout", "text")
        def tick_readout() -> str:
            return str(tick.value)

        @live("pulse")
        def pulse_payload() -> dict[str, object]:
            return {
                "t": round(time.monotonic() - started, 2),
                "n": tick.value,
            }

        @on("pulse-btn", "click")
        def bump() -> None:
            tick.value += 1

    app.run(host="127.0.0.1", port=8003, label="Pulse demo —")


if __name__ == "__main__":
    main()
