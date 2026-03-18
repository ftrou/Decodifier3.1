from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Body, Query

from .patterns import SCHEMAS
from .patterns.runtime import run_pattern_build
from .patterns.spec_loader import load_specs
from .patterns.validator import validate_specs
from .builds import load_latest_build

router = APIRouter(prefix="/patterns", tags=["patterns"])


@router.get("/schemas")
async def list_schemas() -> Dict[str, Any]:
    return {
        "count": len(SCHEMAS),
        "schemas": [
            {
                "pattern": schema.pattern,
                "version": schema.version,
                "fields": [
                    {"name": field.name, "type": field.type, "required": field.required}
                    for field in schema.fields
                ],
            }
            for schema in SCHEMAS.values()
        ],
    }


@router.get("/specs")
async def list_specs(spec_dir: str = Query("patterns/specs")) -> Dict[str, Any]:
    specs = load_specs(spec_dir)
    return {"count": len(specs), "specs": specs}


@router.post("/validate")
async def validate_pattern_specs(spec_dir: str = Body("patterns/specs")) -> Dict[str, Any]:
    specs = load_specs(spec_dir)
    results = validate_specs(specs, SCHEMAS)
    return {
        "count": len(results),
        "results": [
            {
                "pattern": result.schema.pattern,
                "spec_id": result.spec.get("id") or result.spec.get("slug"),
                "errors": result.errors,
                "warnings": result.warnings,
            }
            for result in results
        ],
    }


@router.post("/build")
async def build_from_specs(
    spec_dir: str = Body("patterns/specs"),
    project_root: str = Body("."),
    patterns: List[str] | None = Body(None),
) -> Dict[str, Any]:
    return run_pattern_build(spec_dir=spec_dir, project_root=project_root, patterns=patterns)


@router.get("/builds/latest")
async def latest_build(project_root: str = Query(".")) -> Dict[str, Any]:
    project_id = Path(project_root).name
    payload = load_latest_build(project_id)
    return {"build": payload}
