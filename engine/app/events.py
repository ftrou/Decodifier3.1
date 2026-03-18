from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .paths import data_root


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class Event:
    ts: str
    kind: str
    project_id: str
    payload: Dict[str, Any]


class EventLog:
    """Append-only event log for auditability and 'why did this change?' UX."""

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = (root or data_root()) / "events"
        self.root.mkdir(parents=True, exist_ok=True)

    def append(self, project_id: str, kind: str, payload: Dict[str, Any]) -> Event:
        evt = Event(ts=_utc_now_iso(), kind=kind, project_id=project_id, payload=payload)
        path = self.root / f"{project_id}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(evt.__dict__, ensure_ascii=False) + "\n")
        return evt


event_log = EventLog()
