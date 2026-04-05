"""
Demo: @live pushes a payload; the page listens for the kindling-live CustomEvent.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from kindling import Application, bind, expose, live, on, signal


def main() -> None:
    base = Path(__file__).resolve().parent
    app = Application(template_dir=str(base / "templates"))

    with app.reactive("pulse", path="/", template="index.html"):
        started = time.monotonic()
        tick = signal(0)
        # Recomputed every second so @live can expose a moving clock (time is not reactive).
        wall = signal(False)

        expose(tick=tick)

        def _wall_loop() -> None:
            while True:
                time.sleep(1.0)
                wall.value = not wall.value

        threading.Thread(target=_wall_loop, daemon=True, name="pulse-demo-wall").start()

        @bind("#tick-readout", "text")
        def tick_readout() -> str:
            return str(tick.value)

        @live("pulse")
        def pulse_payload() -> dict[str, object]:
            _ = wall.value
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
