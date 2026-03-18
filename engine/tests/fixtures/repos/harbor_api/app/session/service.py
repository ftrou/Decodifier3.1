from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.models.auth import UserSession
from app.session.repository import save_session


@dataclass
class SessionRecord:
    session_id: str
    subject: str
    expires_at: datetime


def create_session(username: str) -> SessionRecord:
    session = SessionRecord(
        session_id=f"session::{username}",
        subject=username,
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
    )
    save_session(UserSession(session.session_id, username, ["projects:read", "profile:read"]))
    return session


def handle_session_expiration(session: SessionRecord, *, now: datetime) -> bool:
    if session.expires_at <= now:
        return True
    return False
