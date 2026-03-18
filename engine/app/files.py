from pathlib import Path
from fastapi import HTTPException, UploadFile
from unidiff import PatchSet


def resolve_path(root: str, relative_path: str) -> Path:
    candidate = Path(root).joinpath(relative_path).resolve()
    root_path = Path(root).resolve()
    try:
        candidate.relative_to(root_path)
    except ValueError:
        raise HTTPException(status_code=400, detail="Path escapes project root")
    return candidate


def read_file(root: str, relative_path: str) -> str:
    if not relative_path:
        raise HTTPException(status_code=400, detail="Missing path parameter.")
    path = resolve_path(root, relative_path)
    if path.is_dir():
        raise HTTPException(status_code=400, detail="Path is a directory, not a file.")
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Fallback for binary/unknown encodings so the API does not 500
        return path.read_text(encoding="utf-8", errors="ignore")


def write_file(root: str, relative_path: str, content: str) -> None:
    path = resolve_path(root, relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


async def write_upload(root: str, relative_path: str, upload: UploadFile, chunk_size: int = 1024 * 1024) -> None:
    """
    Stream an uploaded file to disk without loading it all into memory.
    """
    path = resolve_path(root, relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        while True:
            chunk = await upload.read(chunk_size)
            if not chunk:
                break
            handle.write(chunk)
    await upload.close()


def apply_patch(root: str, relative_path: str, patch_text: str) -> None:
    if not patch_text.strip():
        raise HTTPException(status_code=400, detail="Empty patch")
    patches = PatchSet(patch_text.splitlines(keepends=True))
    if not patches:
        raise HTTPException(status_code=400, detail="Invalid patch format")

    target_patch = None
    for p in patches:
        patched_name = p.path
        cleaned = patched_name.replace("a/", "").replace("b/", "")
        if cleaned == relative_path or Path(cleaned).name == Path(relative_path).name:
            target_patch = p
            break
    if target_patch is None:
        target_patch = next(iter(patches))

    path = resolve_path(root, relative_path or target_patch.path)
    source_lines = []
    if path.exists():
        source_lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    result: list[str] = []
    idx = 0
    for hunk in target_patch:
        target_start = hunk.target_start or 1
        while idx < target_start - 1 and idx < len(source_lines):
            result.append(source_lines[idx])
            idx += 1
        for line in hunk:
            if line.is_context:
                if idx >= len(source_lines) or source_lines[idx].rstrip("\n") != line.value.rstrip("\n"):
                    raise HTTPException(status_code=409, detail="Context mismatch when applying patch")
                result.append(source_lines[idx])
                idx += 1
            elif line.is_removed:
                if idx >= len(source_lines) or source_lines[idx].rstrip("\n") != line.value.rstrip("\n"):
                    raise HTTPException(status_code=409, detail="Context mismatch when applying patch")
                idx += 1
            elif line.is_added:
                result.append(line.value)
    # append remaining original lines
    result.extend(source_lines[idx:])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(result), encoding="utf-8")
