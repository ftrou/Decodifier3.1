from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, TextIO

from .retrieval import get_context_read_plan, materialize_context, search_symbols

TOOL_SERVER_TOOLS = [
    {
        "name": "search_symbols",
        "description": "Search for the most relevant code symbols for a natural-language query.",
        "arguments": {
            "query": "string",
            "max_symbols": "integer (optional)",
        },
    },
    {
        "name": "get_context_read_plan",
        "description": "Build a bounded read plan for a natural-language code query.",
        "arguments": {
            "query": "string",
            "max_tokens": "integer (optional)",
            "max_symbols": "integer (optional)",
            "max_lines": "integer (optional)",
        },
    },
    {
        "name": "materialize_context",
        "description": "Render a previously generated read plan into bounded code context.",
        "arguments": {
            "plan": "object",
            "max_tokens": "integer (optional)",
            "max_symbols": "integer (optional)",
            "max_lines": "integer (optional)",
        },
    },
]


def _handle_tool_request(root: Path, request: Dict[str, Any]) -> Any:
    tool = request.get("tool")
    args = request.get("arguments") or {}
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
            max_tokens=args.get("max_tokens"),
            max_symbols=args.get("max_symbols"),
            max_lines=args.get("max_lines"),
        )
    raise ValueError(f"unknown tool: {tool}")


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

