from pathlib import Path

from signals import signal

from kindling import Application


def test_render_unwrap_filter(tmp_path: Path):
    tpl_dir = tmp_path / "t"
    tpl_dir.mkdir()
    (tpl_dir / "page.html").write_text("<span>{{ n|unwrap }}</span>", encoding="utf-8")

    app = Application(template_dir=str(tpl_dir))
    n = signal(42)
    r = app.render("page.html", n=n)
    assert r.status == 200
    assert b"<span>42</span>" in r.body
