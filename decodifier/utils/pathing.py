from pathlib import Path


def safe_join(root: str, relpath: str) -> Path:
    """Resolve a relative path under root while blocking traversal."""
    root_path = Path(root).resolve()
    target = (root_path / relpath).resolve()
    if root_path not in target.parents and target != root_path:
        raise ValueError(f"Path traversal blocked: {relpath}")
    return target
