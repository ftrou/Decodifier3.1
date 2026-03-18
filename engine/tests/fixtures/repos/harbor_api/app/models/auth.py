from dataclasses import dataclass


@dataclass
class LoginRequest:
    username: str
    password: str


@dataclass
class UserSession:
    session_id: str
    subject: str
    scopes: list[str]


@dataclass
class AuthTokens:
    access_token: str
    refresh_token: str
