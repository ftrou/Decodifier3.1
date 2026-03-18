from typing import Callable

from fastapi import Request


def add_request_id_header() -> Callable:
    """Attach a simple request id header for tracing in logs."""

    async def middleware(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-DeCodifier-Engine", "v0.1")
        return response

    return middleware
