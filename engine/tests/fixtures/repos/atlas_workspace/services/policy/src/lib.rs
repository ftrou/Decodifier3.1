pub fn permission_scope_label(scope: &str) -> String {
    scope.replace(":", " / ")
}

pub fn token_validation_copy() -> &'static str {
    "Token validation is required before policy evaluation."
}
