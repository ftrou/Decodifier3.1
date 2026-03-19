from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, TextIO

from .retrieval import get_context_read_plan, materialize_context, search_symbols

MCP_TOOL_DEFINITIONS = [
    {
        "name": "search_symbols",
        "title": "Search Symbols",
        "description": "Search for the most relevant code symbols for a natural-language query.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language code query to search for.",
                },
                "max_symbols": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Maximum number of ranked symbols to return.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "annotations": {
            "readOnlyHint": True,
            "openWorldHint": False,
        },
    },
    {
        "name": "get_context_read_plan",
        "title": "Get Context Read Plan",
        "description": "Build a bounded read plan for a natural-language code query.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language code query to plan context for.",
                },
                "max_tokens": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Maximum context token budget for the plan.",
                },
                "max_symbols": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Maximum number of primary symbols to plan around.",
                },
                "max_lines": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Maximum number of lines to materialize per plan.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "annotations": {
            "readOnlyHint": True,
            "openWorldHint": False,
        },
    },
    {
        "name": "materialize_context",
        "title": "Materialize Context",
        "description": "Render a previously generated read plan into bounded code context.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan": {
                    "type": "object",
                    "description": "Plan object returned from get_context_read_plan.",
                },
                "max_tokens": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Maximum context token budget for rendered output.",
                },
                "max_symbols": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Maximum number of symbols to render from the plan.",
                },
                "max_lines": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Maximum number of lines to render from the plan.",
                },
            },
            "required": ["plan"],
            "additionalProperties": False,
        },
        "annotations": {
            "readOnlyHint": True,
            "openWorldHint": False,
        },
    },
]

TOOL_SERVER_TOOLS = [
    {
        "name": tool["name"],
        "description": tool["description"],
        "arguments": {
            key: schema.get("type", "object")
            + (" (optional)" if key not in tool["inputSchema"].get("required", []) else "")
            for key, schema in tool["inputSchema"].get("properties", {}).items()
        },
    }
    for tool in MCP_TOOL_DEFINITIONS
]


def _optional_int(arguments: Dict[str, Any], key: str) -> int | None:
    value = arguments.get(key)
    if value is None:
        return None
    return int(value)


def handle_tool_call(root: Path, tool: str, arguments: Dict[str, Any] | None = None) -> Any:
    args = arguments or {}
    if tool == "list_tools":
        return {"tools": TOOL_SERVER_TOOLS}
    if tool == "search_symbols":
        return {
            "symbols": search_symbols(
                root,
                args["query"],
                max_symbols=int(args.get("max_symbols", 10)),
            )
        }
    if tool == "get_context_read_plan":
        return get_context_read_plan(
            root,
            args["query"],
            max_tokens=int(args.get("max_tokens", 800)),
            max_symbols=int(args.get("max_symbols", 5)),
            max_lines=int(args.get("max_lines", 120)),
        )
    if tool == "materialize_context":
        return materialize_context(
            root,
            args["plan"],
            max_tokens=_optional_int(args, "max_tokens"),
            max_symbols=_optional_int(args, "max_symbols"),
            max_lines=_optional_int(args, "max_lines"),
        )
    raise ValueError(f"unknown tool: {tool}")


def _handle_tool_request(root: Path, request: Dict[str, Any]) -> Any:
    return handle_tool_call(root, request.get("tool"), request.get("arguments"))


def _response(payload: Dict[str, Any], *, outstream: TextIO) -> None:
    outstream.write(json.dumps(payload, sort_keys=True) + "\n")
    outstream.flush()


def run_stdio_tool_server(
    root: str | Path,
    *,
    instream: TextIO = sys.stdin,
    outstream: TextIO = sys.stdout,
) -> int:
    root_path = Path(root).resolve()

    for raw_line in instream:
        line = raw_line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            request_id = request.get("id")
            result = _handle_tool_request(root_path, request)
            _response({"id": request_id, "ok": True, "result": result}, outstream=outstream)
        except Exception as exc:  # pragma: no cover - error path exercised via API contract tests
            request_id = None
            if "request" in locals() and isinstance(request, dict):
                request_id = request.get("id")
            _response(
                {
                    "id": request_id,
                    "ok": False,
                    "error": {"type": exc.__class__.__name__, "message": str(exc)},
                },
                outstream=outstream,
            )

    return 0
