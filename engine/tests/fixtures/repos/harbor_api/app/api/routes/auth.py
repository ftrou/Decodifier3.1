from app.models.auth import AuthTokens, LoginRequest
from app.security.tokens import enforce_token_validation, generate_access_token, generate_refresh_token
from app.session.service import create_session
from app.services.audit import record_login


def login_user(credentials: LoginRequest, *, invitation_token: str | None = None) -> AuthTokens:
    if invitation_token:
        enforce_token_validation(invitation_token)
    session = create_session(credentials.username)
    access_token = generate_access_token(credentials.username)
    refresh_token = generate_refresh_token(session)
    record_login(credentials.username)
    return AuthTokens(access_token=access_token, refresh_token=refresh_token)


def refresh_session(refresh_token: str) -> AuthTokens:
    subject = refresh_token.split("::", 1)[1]
    access_token = generate_access_token(subject)
    replacement_session = create_session(subject)
    rotated_refresh = generate_refresh_token(replacement_session)
    return AuthTokens(access_token=access_token, refresh_token=rotated_refresh)
