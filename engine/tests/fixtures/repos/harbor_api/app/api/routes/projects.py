from app.api.dependencies.current_user import get_current_user
from app.security.permissions import require_project_permission


def list_projects(access_token: str) -> list[dict[str, str]]:
    session = get_current_user(access_token)
    require_project_permission(session, "projects:read")
    return [
        {"id": "proj-001", "name": "North Wharf"},
        {"id": "proj-002", "name": "Drydock"},
    ]
