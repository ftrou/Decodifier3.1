import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .config import get_settings
from .schemas import Project, ProjectCreate
from .paths import data_root
from .events import event_log

CONFIG_PATH = get_settings().project_registry_path


def _ensure_store() -> dict:
    """
    Ensure the projects config file exists and contains valid JSON structure.

    Returns the parsed JSON payload, re-initialising the file with an empty
    structure if it is missing, empty, or malformed.
    """
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    default_payload = {"projects": []}

    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(default_payload, indent=2))
        return default_payload

    try:
        content = CONFIG_PATH.read_text().strip()
        if not content:
            raise ValueError("empty content")
        data = json.loads(content)
        if not isinstance(data, dict) or "projects" not in data:
            raise ValueError("invalid structure")
        return data
    except Exception:
        # Recreate the file with a known-good baseline if parsing fails.
        CONFIG_PATH.write_text(json.dumps(default_payload, indent=2))
        return default_payload


def load_projects() -> List[Project]:
    data = _ensure_store()
    projects = [Project(**p) for p in data.get("projects", [])]

    # Bootstrap a default project that points at the repo root when none exist yet.
    if not projects:
        repo_root = Path(__file__).resolve().parent.parent.parent
        default = Project(
            id=repo_root.name.lower().replace(" ", "-"),
            name=repo_root.name,
            path=str(repo_root),
            ignore=get_settings().default_ignore,
            created_at=datetime.utcnow().isoformat(),
            notes=[],
            packs=[],
        )
        projects = [default]
        save_projects(projects)

    return projects


def save_projects(projects: List[Project]) -> None:
    payload = {"projects": [p.dict() for p in projects]}
    CONFIG_PATH.write_text(json.dumps(payload, indent=2))


def add_project(payload: ProjectCreate) -> Project:
    projects = load_projects()
    project = Project(
        id=payload.name.lower().replace(" ", "-"),
        name=payload.name,
        path=str(Path(payload.path).resolve()),
        ignore=payload.ignore or get_settings().default_ignore,
        created_at=datetime.utcnow().isoformat(),
        notes=[],
        packs=[],
    )
    projects.append(project)
    save_projects(projects)
    event_log.append(project.id, "project_created", {"name": project.name, "path": project.path})
    return project


def get_project(project_id: str) -> Optional[Project]:
    projects = load_projects()
    for project in projects:
        if project.id == project_id:
            return project
    return None


def update_notes(project_id: str, notes: List[str]) -> Optional[Project]:
    projects = load_projects()
    updated = None
    for idx, project in enumerate(projects):
        if project.id == project_id:
            projects[idx] = Project(**{**project.dict(), "notes": notes})
            updated = projects[idx]
            break
    if updated:
        save_projects(projects)
        event_log.append(project_id, "notes_updated", {"count": len(notes)})
    return updated


def update_packs(project_id: str, packs: List[str]) -> Optional[Project]:
    projects = load_projects()
    updated = None
    for idx, project in enumerate(projects):
        if project.id == project_id:
            projects[idx] = Project(**{**project.dict(), "packs": packs})
            updated = projects[idx]
            break
    if updated:
        save_projects(projects)
        event_log.append(project_id, "packs_updated", {"packs": packs})
    return updated
