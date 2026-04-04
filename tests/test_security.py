from kindling import Application, Request
from kindling.response import Response


def test_dispatch_adds_security_headers():
    app = Application()

    @app.get("/x")
    def x(_req: Request) -> Response:
        return Response.build(200, body=b"ok")

    r = app.dispatch(Request.build("GET", "/x"))
    assert r.status == 200
    names = {k.lower(): v for k, v in r.headers}
    assert names.get("x-content-type-options") == "nosniff"
    assert names.get("x-frame-options") == "DENY"
    assert "referrer-policy" in names
