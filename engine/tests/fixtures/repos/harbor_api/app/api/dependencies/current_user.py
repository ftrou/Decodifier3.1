from app.models.auth import UserSession
from app.security.tokens import enforce_token_validation


def get_current_user(access_token: str) -> UserSession:
    payload = enforce_token_validation(access_token)
    return UserSession(
        session_id=f"session::{payload['sub']}",
        subject=payload["sub"],
        scopes=["projects:read", "profile:read"],
    )
