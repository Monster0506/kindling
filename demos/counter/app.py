from __future__ import annotations

from pathlib import Path

from kindling import Application, Request, bind, body, expose, on, signal


def main() -> None:
    base = Path(__file__).resolve().parent
    app = Application(template_dir=str(base / "templates"))

    with app.reactive("counter", path="/", template="index.html"):
        count = signal(0)
        expose(count=count)

        @bind("#readout", "text")
        def readout() -> str:
            return str(count.value)

        @on("inc", "click")
        def inc_click() -> None:
            count.value += 1

        @on("bump-form", "submit")
        def bump_submit(_req: Request) -> None:
            count.value += 1

        @on("reset", "click")
        def reset_click() -> None:
            count.value = 0

    with app.reactive("about", path="/about"):
        @body
        def about_html(_req: Request) -> str:
            return (
                "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'/>"
                "<meta name='viewport' content='width=device-width, initial-scale=1'/>"
                "<title>About</title>"
                "<style>body{font-family:system-ui;padding:2rem;max-width:40rem;line-height:1.5}"
                "code{font-size:0.9em}a{color:#ea580c}</style></head><body>"
                "<p>Raw HTML via <code>@body</code> (no template file; no <code>as scope</code>).</p>"
                "<p>Kindling injects the live config and <code>/_kindling/client.js</code> "
                "before <code>&lt;/body&gt;</code> when you omit them.</p>"
                "<p><a href='/def'>LivePage without <code>reactive</code> -></a></p>"
                "<p>Back to <a href='/'>counter</a>.</p>"
                "</body></html>"
            )

    @app.page("/def")
    def def_page(_req: Request) -> str:
        return (
            "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'/>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'/>"
            "<title>Definitions</title>"
            "<style>body{font-family:system-ui;padding:2rem;max-width:40rem;line-height:1.5}"
            "code{font-size:0.9em}a{color:#ea580c}dl dt{font-weight:600;margin-top:1rem}</style></head><body>"
            "<h1>Definitions</h1>"
            "<dl>"
            "<dt>Signal</dt><dd>Reactive cell; reads/writes use <code>.value</code>.</dd>"
            "<dt>LivePage</dt><dd>GET/POST on one path; morph after POST when the client script runs.</dd>"
            "<dt><code>app.page</code></dt><dd>Registers a LivePage from a function; no reactive scope.</dd>"
            "</dl>"
            "<p><a href='/about'>About</a> | <a href='/'>Counter</a></p>"
            "</body></html>"
        )

    app.run(host="127.0.0.1", port=8001, label="Counter demo -")


if __name__ == "__main__":
    main()
