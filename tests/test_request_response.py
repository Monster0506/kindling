from kindling.request import Request
from kindling.response import (
    Response,
    html_response,
    internal_server_error,
    json_response,
    not_found,
    text_response,
)


def test_request_form_urlencoded():
    body = b"a=1&b=two+things&a=second"
    req = Request.build(
        "POST",
        "/submit",
        headers=(
            ("Content-Type", "application/x-www-form-urlencoded"),
            ("Host", "localhost"),
        ),
        body=body,
    )
    assert req.form["a"] == ["1", "second"]
    assert req.form_value("b") == "two things"
    assert req.form_value("missing") is None


def test_response_factories():
    t = text_response("hi")
    assert t.status == 200
    assert t.body == b"hi"
    assert any(v == "text/plain; charset=utf-8" for _, v in t.headers)

    h = html_response("<p>x</p>")
    assert b"<p>x</p>" in h.body
    j = json_response({"n": 1})
    assert j.body == b'{"n":1}'

    n = not_found()
    assert n.status == 404
    e = internal_server_error()
    assert e.status == 500

    r = Response.build(201, body=b"ok", headers=(("X-Foo", "bar"),))
    assert r.status == 201
    assert r.body == b"ok"
