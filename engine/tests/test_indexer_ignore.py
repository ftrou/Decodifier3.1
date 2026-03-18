from pathlib import Path

from engine.app import indexer
from engine.app.schemas import Project


def build_project(root: Path) -> Project:
    return Project(id="p1", name="Project", path=str(root))


def test_should_skip_uses_default_ignores(tmp_path: Path) -> None:
    project = build_project(tmp_path)

    ignored = [
        tmp_path / "node_modules" / "lib.js",
        tmp_path / ".decodifier" / "chroma.db",
        tmp_path / "frontend" / "node_modules" / "react.js",
        tmp_path / "venv" / "bin" / "activate",
        tmp_path / "src" / "__pycache__" / "main.pyc",
        tmp_path / "build" / "artifact.pyc",
    ]
    for path in ignored:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        assert indexer._should_skip(path, project) is True


def test_should_skip_enforces_extension_allowlist(tmp_path: Path) -> None:
    project = build_project(tmp_path)

    allowed = tmp_path / "src" / "main.py"
    allowed.parent.mkdir(parents=True, exist_ok=True)
    allowed.write_text("print('hi')")
    assert indexer._should_skip(allowed, project) is False

    blocked = tmp_path / "docs" / "notes.txt"
    blocked.parent.mkdir(parents=True, exist_ok=True)
    blocked.write_text("plain text")
    assert indexer._should_skip(blocked, project) is True
