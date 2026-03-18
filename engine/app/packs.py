from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .paths import data_root
from .policy import PolicyViolation


@dataclass(frozen=True)
class PackInfo:
    name: str
    path: str
    manifest: Dict


class PackRegistry:
    """
    Packs live in:
      <DATA_ROOT>/packs/<name>/

    Each pack should include:
      - pack.yaml  (manifest: name, version, description, optional deps)
      - specs/     (yaml spec files)
    """

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = (root or data_root()) / "packs"
        self.root.mkdir(parents=True, exist_ok=True)

    def list(self) -> List[PackInfo]:
        out: List[PackInfo] = []
        for pack_dir in sorted(self.root.glob("*")):
            if not pack_dir.is_dir():
                continue
            manifest_path = pack_dir / "pack.yaml"
            if not manifest_path.exists():
                continue
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
            out.append(PackInfo(name=pack_dir.name, path=str(pack_dir), manifest=manifest))
        return out

    def install_from_dir(
        self,
        source_dir: str | Path,
        *,
        name: Optional[str] = None,
        overwrite: bool = False,
    ) -> PackInfo:
        src = Path(source_dir).resolve()
        if not src.is_dir():
            raise PolicyViolation(code="PACK_SOURCE_INVALID", message=f"Pack source is not a directory: {str(src)!r}")

        manifest_path = src / "pack.yaml"
        if not manifest_path.exists():
            raise PolicyViolation(code="PACK_MANIFEST_MISSING", message="pack.yaml is required at the pack root.")

        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        pack_name = name or manifest.get("name") or src.name

        dest = (self.root / pack_name).resolve()
        if dest.exists():
            if not overwrite:
                raise PolicyViolation(code="PACK_EXISTS", message=f"Pack already installed: {pack_name!r}")
            shutil.rmtree(dest)

        shutil.copytree(src, dest)
        return PackInfo(name=pack_name, path=str(dest), manifest=manifest)

    def list_specs(self, pack_names: List[str]) -> List[Dict[str, str]]:
        specs: List[Dict[str, str]] = []
        for name in pack_names:
            pack_dir = self.root / name
            if not pack_dir.exists():
                raise PolicyViolation(code="PACK_NOT_INSTALLED", message=f"Pack not installed: {name!r}")
            specs_dir = pack_dir / "specs"
            if not specs_dir.exists():
                continue
            candidates = list(specs_dir.glob("*.yaml")) + list(specs_dir.glob("*.yml"))
            for spec_path in sorted(candidates, key=lambda path: path.name):
                specs.append(
                    {
                        "pack": name,
                        "path": str(spec_path.relative_to(pack_dir)),
                        "content": spec_path.read_text(encoding="utf-8"),
                    }
                )
        return specs


pack_registry = PackRegistry()


def get_project_specs(project_id: str) -> List[Dict[str, str]]:
    from . import storage

    project = storage.get_project(project_id)
    if not project:
        raise ValueError("Project not found")
    return pack_registry.list_specs(project.packs or [])
