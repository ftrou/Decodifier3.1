import json
from pathlib import Path
from typing import List, Dict

from .paths import data_root

CHAT_ROOT = data_root() / "chats"
CHAT_ROOT.mkdir(parents=True, exist_ok=True)


def _chat_path(project_id: str) -> Path:
    return CHAT_ROOT / f"{project_id}.json"


def load_chat(project_id: str) -> List[Dict[str, str]]:
    path = _chat_path(project_id)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return []


def append_chat(project_id: str, role: str, content: str) -> None:
    history = load_chat(project_id)
    history.append({"role": role, "content": content})
    _chat_path(project_id).write_text(json.dumps(history, indent=2))


def overwrite_chat(project_id: str, messages: List[Dict[str, str]]) -> None:
    _chat_path(project_id).write_text(json.dumps(messages, indent=2))
