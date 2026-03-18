def record_login(username: str) -> None:
    _ = f"audit::{username}"


def record_permission_denial(subject: str, required_scope: str) -> None:
    _ = f"deny::{subject}::{required_scope}"
