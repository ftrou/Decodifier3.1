from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, TextIO

from .tool_server import MCP_TOOL_DEFINITIONS, handle_tool_call

DEFAULT_PROTOCOL_VERSION = "2025-03-26"
SUPPORTED_PROTOCOL_VERSIONS = {
    "2024-11-05",
    "2025-03-26",
    "2025-06-18",
    "2025-11-05",
}
SERVER_INFO = {"name": "decodifier", "version": "0.1.0"}
SERVER_CAPABILITIES = {"tools": {"listChanged": False}}
SERVER_INSTRUCTIONS = (
    "Use search_symbols first for broad retrieval, then get_context_read_plan, and "
    "materialize_context only when bounded code context is required."
)
SUPPORTED_TOOL_NAMES = {tool["name"] for tool in MCP_TOOL_DEFINITIONS}


def _response(payload: Dict[str, Any], *, outstream: TextIO) -> None:
    outstream.write(json.dumps(payload, sort_keys=True) + "\n")
    outstream.flush()


def _error_response(
    request_id: Any,
    code: int,
    message: str,
    *,
    outstream: TextIO,
) -> None:
    _response(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        },
        outstream=outstream,
    )


def _negotiate_protocol_version(requested: Any) -> str:
    if isinstance(requested, str) and requested in SUPPORTED_PROTOCOL_VERSIONS:
        return requested
    return DEFAULT_PROTOCOL_VERSION


def _text_content(payload: Any) -> list[Dict[str, str]]:
    return [{"type": "text", "text": json.dumps(payload, indent=2, sort_keys=True)}]


def _handle_request(root: Path, request: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any] | None:
    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params") or {}

    if method == "initialize":
        protocol_version = _negotiate_protocol_version(params.get("protocolVersion"))
        state["initialized"] = True
        state["protocol_version"] = protocol_version
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": protocol_version,
                "capabilities": SERVER_CAPABILITIES,
                "serverInfo": SERVER_INFO,
                "instructions": SERVER_INSTRUCTIONS,
            },
        }

    if method == "notifications/initialized":
        state["client_initialized"] = True
        return None

    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": MCP_TOOL_DEFINITIONS}}

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name not in SUPPORTED_TOOL_NAMES:
            raise ValueError(f"unknown tool: {name}")
        try:
            result = handle_tool_call(root, name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": _text_content(result),
                    "structuredContent": result,
                    "isError": False,
                },
            }
        except Exception as exc:
            error_payload = {"type": exc.__class__.__name__, "message": str(exc)}
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": _text_content(error_payload),
                    "structuredContent": error_payload,
                    "isError": True,
                },
            }

    if method == "resources/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"resources": []}}

    if method == "prompts/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"prompts": []}}

    raise ValueError(f"unknown method: {method}")


def _read_message(instream: TextIO) -> Dict[str, Any] | None:
    while True:
        line = instream.readline()
        if line == "":
            return None
        stripped = line.strip()
        if stripped:
            break

    payload = json.loads(stripped)
    if not isinstance(payload, dict):
        raise ValueError("invalid request payload")
    return payload


def run_stdio_mcp_server(
    root: str | Path,
    *,
    instream: TextIO = sys.stdin,
    outstream: TextIO = sys.stdout,
) -> int:
    root_path = Path(root).resolve()
    state: Dict[str, Any] = {"initialized": False, "client_initialized": False}

    while True:
        request_id: Any = None
        try:
            request = _read_message(instream)
            if request is None:
                break
            request_id = request.get("id")
            response = _handle_request(root_path, request, state)
            if response is not None and request_id is not None:
                _response(response, outstream=outstream)
        except json.JSONDecodeError as exc:
            _error_response(request_id, -32700, f"parse error: {exc.msg}", outstream=outstream)
        except ValueError as exc:
            _error_response(request_id, -32601, str(exc), outstream=outstream)
        except Exception as exc:  # pragma: no cover - defensive server fallback
            _error_response(request_id, -32603, f"{exc.__class__.__name__}: {exc}", outstream=outstream)

    return 0
