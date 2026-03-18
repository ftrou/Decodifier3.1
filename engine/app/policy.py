from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import get_settings, DEFAULT_IGNORE


@dataclass(frozen=True)
class PolicyViolation(Exception):
    code: str
    message: str
    hint: Optional[str] = None

    def as_dict(self) -> dict:
        data = {"code": self.code, "message": self.message}
        if self.hint:
            data["hint"] = self.hint
        return data


class PolicyEngine:
    """
    Central place for non-negotiable safety & determinism policies.
    - filesystem sandboxing (no traversal / no outside-root)
    - deny writes to ignored/hidden dirs
    - size guards for writes
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    def normalize_relpath(self, relpath: str) -> str:
        rel = relpath.replace("\\", "/").lstrip("/")
        p = Path(rel)
        if any(part in ("..", "") for part in p.parts):
            raise PolicyViolation(
                code="PATH_TRAVERSAL",
                message=f"Path traversal is not allowed: {relpath!r}",
                hint="Use a repo-relative path like 'patterns/specs/app.yaml'.",
            )
        return str(p)

    def ensure_allowed_path(self, project_root: str | Path, relpath: str, *, op: str) -> Path:
        root = Path(project_root).resolve()
        rel = self.normalize_relpath(relpath)
        full = (root / rel).resolve()

        try:
            full.relative_to(root)
        except Exception:
            raise PolicyViolation(
                code="OUTSIDE_PROJECT",
                message=f"Operation would access outside project root: {rel!r}",
                hint="Only files under the selected project root are allowed.",
            )

        ignore = set(DEFAULT_IGNORE) | set(self.settings.default_ignore)
        parts = Path(rel).parts

        if any(part in ignore for part in parts):
            raise PolicyViolation(
                code="IGNORED_PATH",
                message=f"Path is ignored by policy: {rel!r}",
                hint=f"Move the file outside ignored directories: {sorted(ignore)}",
            )

        if any(part.startswith(".") and part not in (".",) for part in parts):
            raise PolicyViolation(
                code="HIDDEN_PATH",
                message=f"Hidden paths are not writable: {rel!r}",
                hint="Avoid writing into dot-directories unless explicitly allowed.",
            )

        return full

    def ensure_write_size(self, content: str, *, max_bytes: int = 2_000_000) -> None:
        if len(content.encode("utf-8", errors="ignore")) > max_bytes:
            raise PolicyViolation(
                code="FILE_TOO_LARGE",
                message=f"Write refused: content exceeds {max_bytes} bytes.",
                hint="Write smaller chunks or increase the policy limit intentionally.",
            )


policy_engine = PolicyEngine()
