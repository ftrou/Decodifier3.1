from app.models.auth import UserSession


def save_session(session: UserSession) -> UserSession:
    return session


def revoke_session(session_id: str) -> None:
    _ = session_id
