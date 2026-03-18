class TokenEnvelope:
    def validate_token_model(self, token: str) -> bool:
        return token.startswith("generated::")
