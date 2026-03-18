from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import yaml


@dataclass
class FieldDef:
    name: str
    type: str | None = None
    required: bool = False
    description: str | None = None


@dataclass
class Schema:
    pattern: str
    fields: List[FieldDef]
    outputs_template: str
    version: str = "1.0.0"


def load_schemas(path: str | Path) -> Dict[str, Schema]:
    """Load pattern schemas from v1_schemas.yaml."""
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    schemas: Dict[str, Schema] = {}
    for entry in data.get("schemas", []):
        pattern = entry["pattern"]
        fields = [
            FieldDef(
                name=field["name"],
                type=field.get("type"),
                required=bool(field.get("required", False)),
                description=field.get("description"),
            )
            for field in entry.get("fields", [])
        ]
        schemas[pattern] = Schema(
            pattern=pattern,
            fields=fields,
            outputs_template=entry.get("outputs_template", ""),
            version=entry.get("version", data.get("version", "1.0.0")),
        )
    return schemas
