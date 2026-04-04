from pathlib import Path

import pytest

from kindling import Application, signal


def test_signal_outside_reactive_raises():
    with pytest.raises(RuntimeError, match="reactive scope"):
        signal(0)


def test_nested_reactive_raises(tmp_path: Path):
    (tmp_path / "a.html").write_text("a", encoding="utf-8")
    app = Application(template_dir=str(tmp_path))
    with pytest.raises(RuntimeError, match="Nested"):
        with app.reactive("outer", path="/o", template="a.html"):
            with app.reactive("inner", path="/i", template="a.html"):
                pass


def test_duplicate_reactive_name_raises(tmp_path: Path):
    (tmp_path / "t.html").write_text("x", encoding="utf-8")
    app = Application(template_dir=str(tmp_path))
    with app.reactive("same", path="/a", template="t.html"):
        signal(1)
    with pytest.raises(ValueError, match="Duplicate reactive scope name"):
        with app.reactive("same", path="/b", template="t.html"):
            pass


def test_duplicate_reactive_path_raises(tmp_path: Path):
    (tmp_path / "t.html").write_text("x", encoding="utf-8")
    app = Application(template_dir=str(tmp_path))
    with app.reactive("one", path="/shared", template="t.html"):
        signal(1)
    with pytest.raises(ValueError, match="Duplicate reactive path"):
        with app.reactive("two", path="/shared", template="t.html"):
            pass
