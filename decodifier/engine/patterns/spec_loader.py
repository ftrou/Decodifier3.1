from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml


ROOT = Path(__file__).resolve().parents[3]


def _load_app_use_list(spec_dir: Path) -> list[str]:
    """Read app.yaml/app.yml for a `use:` list of packs, if present."""
    for name in ("app.yaml", "app.yml"):
        path = spec_dir / name
        if path.exists():
            doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            return list(doc.get("use", []) or [])
    return []


def _full_spec_id(slug: str) -> str:
    """Normalize spec slug into a globally unique id (pattern.slug style)."""
    return slug


def _normalize_spec(spec: Dict[str, Any], *, default_id: str | None = None) -> Dict[str, Any]:
    normalized = spec
    if "kind" in normalized and isinstance(normalized["kind"], str):
        kind = normalized["kind"].lower().strip()
        if kind != normalized["kind"]:
            normalized = dict(normalized)
            normalized["kind"] = kind
    if "pattern" not in normalized and "kind" in normalized:
        if normalized is spec:
            normalized = dict(normalized)
        normalized["pattern"] = normalized["kind"]
    if "pattern" in normalized and isinstance(normalized["pattern"], str):
        pattern = normalized["pattern"].lower().strip()
        if pattern != normalized["pattern"]:
            if normalized is spec:
                normalized = dict(normalized)
            normalized["pattern"] = pattern
    if "method" in normalized and isinstance(normalized["method"], str):
        method = normalized["method"].upper().strip()
        if method != normalized["method"]:
            if normalized is spec:
                normalized = dict(normalized)
            normalized["method"] = method
    if "id" not in normalized and default_id:
        if normalized is spec:
            normalized = dict(normalized)
        normalized["id"] = default_id
    return normalized


def _extract_specs(doc: Any, *, source: str) -> Iterable[Dict[str, Any]]:
    if isinstance(doc, list):
        for entry in doc:
            if isinstance(entry, dict):
                yield entry
        return
    if isinstance(doc, dict):
        if "pattern" in doc or "kind" in doc:
            yield doc
            return
        for slug, entry in doc.items():
            if isinstance(entry, dict):
                yield _normalize_spec(entry, default_id=str(slug))
        return
    raise ValueError(f"Unsupported spec format in {source}")


def _load_specs_from_dir(spec_dir: Path) -> Dict[str, Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for path in sorted(spec_dir.glob("*.y*ml")):
        if path.name in ("app.yaml", "app.yml"):
            continue
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for spec in _extract_specs(doc, source=str(path)):
            if spec.get("skip") is True:
                continue
            spec = _normalize_spec(spec, default_id=path.stem)
            slug = spec.get("id") or spec.get("slug") or path.stem
            full_slug = _full_spec_id(str(slug))
            if full_slug in merged:
                raise ValueError(f"Duplicate spec slug in {spec_dir}: {full_slug}")
            merged[full_slug] = spec
    return merged


def load_pack(pack_name: str) -> Dict[str, Dict[str, Any]]:
    pack_dir = ROOT / "packs" / pack_name / "specs"
    if not pack_dir.exists():
        raise ValueError(f"Pack not found: {pack_name}")
    specs = _load_specs_from_dir(pack_dir)
    namespaced: Dict[str, Dict[str, Any]] = {}
    for slug, spec in specs.items():
        namespaced[f"{pack_name}.{slug}"] = spec
    return namespaced


def load_specs(spec_dir: str | Path) -> List[Dict[str, Any]]:
    """
    Merge specs from packs (declared in app.yaml/app.yml) and local specs.
    Returns a flat list of spec dicts.
    """
    spec_dir = Path(spec_dir)

    use_list = _load_app_use_list(spec_dir)
    pack_specs: Dict[str, Dict[str, Any]] = {}
    for pack_name in use_list:
        pack_specs.update(load_pack(pack_name))

    local_specs = _load_specs_from_dir(spec_dir)

    merged: Dict[str, Dict[str, Any]] = {}
    merged.update(pack_specs)
    merged.update(local_specs)
    return list(merged.values())
