from app.session.service import SessionRecord


def generate_access_token(subject: str) -> str:
    return f"access::{subject}"


def generate_refresh_token(session: SessionRecord) -> str:
    return f"refresh::{session.session_id}"


def decode_access_token(token: str) -> dict[str, str]:
    if not token.startswith("access::") and not token.startswith("invite::"):
        raise ValueError("unsupported token")
    subject = token.split("::", 1)[1]
    status = "expired" if subject.endswith("-expired") else "active"
    return {"sub": subject, "status": status}


def enforce_token_validation(token: str) -> dict[str, str]:
    payload = decode_access_token(token)
    if payload["status"] != "active":
        raise ValueError("token validation failed")
    return payload
