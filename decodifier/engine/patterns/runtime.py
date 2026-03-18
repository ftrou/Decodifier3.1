from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from . import SCHEMAS
from .spec_loader import load_specs
from .validator import validate_specs
from ..builds import record_pattern_build
from ..generators.backend_http_endpoint import generate_http_endpoint


def run_pattern_build(
    spec_dir: str | Path,
    project_root: str | Path,
    patterns: List[str] | None = None,
) -> Dict[str, Any]:
    """
    High-level entrypoint:
    - Load specs (packs + local)
    - Validate against schemas
    - Generate code for selected patterns
    - Record build metadata
    """
    spec_dir = Path(spec_dir)
    project_root = Path(project_root)

    specs = load_specs(spec_dir)
    results = validate_specs(specs, SCHEMAS)

    diagnostics = []
    valid_specs: List[Dict[str, Any]] = []
    for result in results:
        diag = {
            "pattern": result.schema.pattern,
            "errors": result.errors,
            "warnings": result.warnings,
            "spec_id": result.spec.get("id") or result.spec.get("slug"),
        }
        diagnostics.append(diag)
        if result.ok:
            valid_specs.append(result.spec)

    if patterns:
        valid_specs = [spec for spec in valid_specs if spec.get("pattern") in patterns]

    files_written: List[str] = []
    pattern_ids = sorted({spec.get("pattern") for spec in valid_specs if spec.get("pattern")})

    for spec in valid_specs:
        pattern = spec["pattern"]
        if pattern == "backend.http_endpoint":
            files = generate_http_endpoint(spec, project_root)
            files_written.extend([str(path) for path in files])

    files_written = sorted(set(files_written))

    meta = {
        "pattern_ids": pattern_ids,
        "project_id": project_root.name,
        "specs_used": [spec.get("id") or spec.get("slug") for spec in valid_specs],
        "files_written": files_written,
        "diagnostics": diagnostics,
    }
    record_pattern_build(meta)
    return meta
