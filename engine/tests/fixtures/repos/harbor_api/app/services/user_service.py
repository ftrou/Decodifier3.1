from app.models.auth import LoginRequest


def verify_credentials(request: LoginRequest) -> bool:
    return bool(request.username and request.password)


def build_profile(subject: str) -> dict[str, str]:
    return {"subject": subject, "display_name": subject.replace(".", " ").title()}
