from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


ROOT = Path(__file__).resolve().parents[2]


def record_pattern_build(meta: Dict[str, Any]) -> Path:
    """
    Record a Decodifier build run to .builds/builds.jsonl.

    Expected meta fields:
      - pattern_ids: list[str]
      - project_id: str
      - specs_used: list[str]
      - files_written: list[str]
      - diagnostics: list[dict]
    """
    builds_dir = ROOT / ".builds"
    builds_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(tz=timezone.utc).isoformat()
    payload = dict(meta)
    payload["timestamp"] = timestamp

    log_path = builds_dir / "builds.jsonl"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    return log_path


def load_latest_build(project_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    log_path = ROOT / ".builds" / "builds.jsonl"
    if not log_path.exists():
        return None
    lines = log_path.read_text(encoding="utf-8").splitlines()
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if project_id and payload.get("project_id") != project_id:
            continue
        return payload
    return None
