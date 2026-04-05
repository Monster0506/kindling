from __future__ import annotations

from pathlib import Path

from signals import signal as sig

from kindling import Application, Request, bind, expose, json_response, on


def main() -> None:
    base = Path(__file__).resolve().parent
    app = Application(template_dir=str(base / "templates"))

    count = sig(0)

    with app.reactive("home", path="/", template="index.html"):
        expose(count=count)

        @bind("#readout", "text")
        def readout() -> str:
            return str(count.value)

        @on("inc", "click")
        def inc_click() -> None:
            count.value += 1

    @app.get("/api/hello")
    def api_hello(_req: Request):
        return json_response(
            {
                "ok": True,
                "count": count.value,
                "from": "kindling",
                "hint": "same signal as / readout, bump on / then refresh this JSON",
            }
        )

    app.run(host="127.0.0.1", port=8000, label="Routes demo -")


if __name__ == "__main__":
    main()
