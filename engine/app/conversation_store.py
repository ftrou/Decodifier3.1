import json
from pathlib import Path
from typing import Dict, Any

from . import chat_store
from .paths import data_root

CONVO_ROOT = data_root() / "conversations"
CONVO_ROOT.mkdir(parents=True, exist_ok=True)


def _path(project_id: str) -> Path:
    return CONVO_ROOT / f"{project_id}.json"


def load_state(project_id: str) -> Dict[str, Any]:
    path = _path(project_id)
    if not path.exists():
        return {"conversations": [], "active_id": None}
    try:
        data = json.loads(path.read_text())
        convos = data.get("conversations", [])
        active = data.get("active_id")
        return {"conversations": convos, "active_id": active}
    except json.JSONDecodeError:
        return {"conversations": [], "active_id": None}


def _seed_from_legacy(project_id: str) -> Dict[str, Any]:
    legacy = chat_store.load_chat(project_id)
    if not legacy:
        return {"conversations": [], "active_id": None}
    seeded = {
        "conversations": [{"id": f"{project_id}-live", "title": "Live session", "messages": legacy}],
        "active_id": f"{project_id}-live",
    }
    save_state(project_id, seeded)
    return seeded


def load_state_with_seed(project_id: str) -> Dict[str, Any]:
    state = load_state(project_id)
    if state["conversations"]:
        return state
    return _seed_from_legacy(project_id)


def save_state(project_id: str, state: Dict[str, Any]) -> None:
    _path(project_id).write_text(json.dumps(state, indent=2))


def ensure_conversation(project_id: str, convo_id: str, title: str = "Live session") -> Dict[str, Any]:
    state = load_state(project_id)
    convos = state.get("conversations", [])
    existing = next((c for c in convos if c.get("id") == convo_id), None)
    if existing:
        if title and existing.get("title") != title:
            existing["title"] = title
    else:
        convos.insert(0, {"id": convo_id, "title": title or "Session", "messages": []})
    state["conversations"] = convos
    if not state.get("active_id"):
        state["active_id"] = convo_id
    save_state(project_id, state)
    return state


def append_message(project_id: str, convo_id: str, message: Dict[str, Any], title: str = "Live session") -> None:
    state = ensure_conversation(project_id, convo_id, title)
    for convo in state["conversations"]:
        if convo["id"] == convo_id:
            convo.setdefault("messages", []).append(message)
            break
    save_state(project_id, state)


def set_active(project_id: str, convo_id: str) -> Dict[str, Any]:
    state = load_state_with_seed(project_id)
    state["active_id"] = convo_id
    save_state(project_id, state)
    return state
