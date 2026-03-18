def build_permission_digest(subject: str) -> str:
    return f"permission digest for {subject}"


def permission_scope_label(scope: str) -> str:
    return scope.replace(":", " / ")
