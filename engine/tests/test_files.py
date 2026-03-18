from pathlib import Path

import pytest
from fastapi import HTTPException

from engine.app import files


def test_resolve_path_blocks_traversal(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()

    with pytest.raises(HTTPException) as excinfo:
        files.resolve_path(str(project_root), "../outside.txt")

    assert excinfo.value.status_code == 400


def test_resolve_path_allows_descendant(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    target_dir = project_root / "src"
    target_dir.mkdir(parents=True)

    resolved = files.resolve_path(str(project_root), "src/example.py")

    assert resolved == target_dir / "example.py"


def test_apply_patch_creates_and_updates_file(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    target = project_root / "hello.txt"

    creation_patch = """--- a/hello.txt
+++ b/hello.txt
@@ -0,0 +1 @@
+hello
"""
    files.apply_patch(str(project_root), "hello.txt", creation_patch)
    assert target.read_text() == "hello\n"

    append_patch = """--- a/hello.txt
+++ b/hello.txt
@@ -1 +1,2 @@
-hello
+hello
+world
"""
    files.apply_patch(str(project_root), "hello.txt", append_patch)
    assert target.read_text().splitlines() == ["hello", "world"]


def test_apply_patch_rejects_context_mismatch(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    target = project_root / "hello.txt"
    target.write_text("hello\n")

    bad_patch = """--- a/hello.txt
+++ b/hello.txt
@@ -1 +1 @@
-goodbye
+hola
"""
    with pytest.raises(HTTPException) as excinfo:
        files.apply_patch(str(project_root), "hello.txt", bad_patch)

    assert excinfo.value.status_code == 409
