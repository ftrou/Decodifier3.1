from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import difflib

from .schema_registry import Schema


@dataclass
class ValidationResult:
    spec: Dict[str, Any]
    schema: Schema
    errors: List[str]
    warnings: List[str]

    @property
    def ok(self) -> bool:
        return not self.errors


FIELD_HINTS: Dict[tuple[str, str], str] = {}


def diagnose_spec(spec: Dict[str, Any], schema: Schema) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []

    allowed_fields = {field.name for field in schema.fields}
    required_fields = {field.name for field in schema.fields if field.required}

    pattern = spec.get("pattern")
    if pattern != schema.pattern:
        errors.append(f"Spec pattern '{pattern}' does not match schema '{schema.pattern}'.")

    for field in required_fields:
        if field not in spec or spec[field] in (None, ""):
            msg = f"Missing required field '{field}' for pattern {schema.pattern}."
            hint = FIELD_HINTS.get((schema.pattern, field))
            if hint:
                msg += f"\n\nHint:\n{hint}"
            errors.append(msg)

    method_field = next((field for field in schema.fields if field.name == "method"), None)
    if method_field and isinstance(spec.get("method"), str):
        field_type = method_field.type or ""
        if field_type.startswith("enum[") and field_type.endswith("]"):
            raw_values = field_type[len("enum[") : -1]
            valid = [value.strip() for value in raw_values.split(",") if value.strip()]
            if valid and spec["method"].upper() not in {value.upper() for value in valid}:
                errors.append(
                    f"Invalid method '{spec['method']}'. Expected one of {valid}."
                )

    extras = [key for key in spec.keys() if key not in allowed_fields and key not in {"pattern"}]
    for extra in extras:
        msg = (
            f"Field '{extra}' is not part of schema {schema.pattern}. "
            "It will be ignored unless you update the schema."
        )
        close = difflib.get_close_matches(extra, allowed_fields, n=1, cutoff=0.78)
        if close:
            msg += f" Did you mean '{close[0]}'?"
        warnings.append(msg)

    return ValidationResult(spec=spec, schema=schema, errors=errors, warnings=warnings)


def validate_specs(specs: List[Dict[str, Any]], schemas: Dict[str, Schema]) -> List[ValidationResult]:
    results: List[ValidationResult] = []
    for spec in specs:
        pattern = spec.get("pattern")
        if pattern not in schemas:
            results.append(
                ValidationResult(
                    spec,
                    Schema(pattern or "unknown", [], "", "1.0.0"),
                    errors=[f"No schema registered for pattern '{pattern}'."],
                    warnings=[],
                )
            )
            continue
        results.append(diagnose_spec(spec, schemas[pattern]))
    return results
