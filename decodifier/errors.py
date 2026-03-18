from typing import Any, Optional


class DeCodifierError(Exception):
    """Generic error when talking to the DeCodifier backend."""

    def __init__(self, message: str, status_code: Optional[int] = None, payload: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload
