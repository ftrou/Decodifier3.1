from app.models.auth import UserSession


def has_scope(scopes: list[str], required_scope: str) -> bool:
    return required_scope in scopes


def require_project_permission(session: UserSession, required_scope: str) -> None:
    if not has_scope(session.scopes, required_scope):
        raise PermissionError(f"missing {required_scope}")
