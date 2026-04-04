from kindling import Application, Request


def test_get_404_when_unmatched():
    app = Application()
    req = Request.build("GET", "/nope")
    r = app.dispatch(req)
    assert r.status == 404


def test_registered_get_returns_body():
    app = Application()

    @app.get("/hello")
    def hello(_req: Request) -> str:
        return "<p>hi</p>"

    r = app.dispatch(Request.build("GET", "/hello"))
    assert r.status == 200
    assert b"<p>hi</p>" in r.body


def test_route_params_on_request():
    app = Application()

    @app.get("/hello/{name}")
    def hello(req: Request) -> str:
        return f"<p>{req.route_params['name']}</p>"

    r = app.dispatch(Request.build("GET", "/hello/world"))
    assert r.status == 200
    assert b"world" in r.body
