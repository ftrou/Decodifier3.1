from pathlib import Path

from .schema_registry import load_schemas

ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = load_schemas(ROOT / "patterns" / "v1_schemas.yaml")

__all__ = ["SCHEMAS"]
