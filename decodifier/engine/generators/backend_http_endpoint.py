from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List


def _normalize_handler_name(raw: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9_]", "_", raw.strip())
    if not name:
        return "generated_handler"
    if name[0].isdigit():
        name = f"handler_{name}"
    return name


def _parse_path_params(route_path: str) -> List[str]:
    matches = re.findall(r"{([^}]+)}", route_path)
    params: List[str] = []
    for match in matches:
        name = match.split(":", 1)[0].split("=", 1)[0].strip()
        if not name:
            continue
        if name not in params:
            params.append(name)
    return params


def generate_http_endpoint(spec: Dict[str, Any], project_root: Path) -> List[Path]:
    """
    Generate backend HTTP endpoint code from a backend.http_endpoint spec.

    This is intentionally minimal; wire full templates when you lock the schema.
    """
    pattern = spec.get("pattern")
    if pattern != "backend.http_endpoint":
        raise ValueError(f"Unsupported pattern for this generator: {pattern}")

    route_path = spec.get("path") or "/placeholder"
    method = (spec.get("method") or "post").lower()
    handler_name = _normalize_handler_name(str(spec.get("id") or spec.get("name") or "generated_handler"))
    path_params = _parse_path_params(route_path)

    backend_dir = project_root / "backend"
    api_path = backend_dir / "api" / "generated_endpoints.py"
    api_path.parent.mkdir(parents=True, exist_ok=True)

    existing = api_path.read_text(encoding="utf-8") if api_path.exists() else ""
    if not existing:
        existing = "from fastapi import APIRouter\n\nrouter = APIRouter()\n"

    if f"def {handler_name}" in existing:
        return [api_path]

    args = ", ".join(f"{param}: str" for param in path_params)
    return_items = [f"\"status\": \"ok\"", f"\"handler\": \"{handler_name}\""]
    return_items.extend([f"\"{param}\": {param}" for param in path_params])
    return_payload = "{" + ", ".join(return_items) + "}"

    snippet = f"""

@router.{method}("{route_path}")
async def {handler_name}({args}):
    return {return_payload}
"""

    api_path.write_text(existing + snippet, encoding="utf-8")
    return [api_path]
