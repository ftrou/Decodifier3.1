from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path
from typing import Sequence

GENERIC_PYTHON_PLACEHOLDER = "/path/to/python"


def _server_command(
    repo_root: str | Path | None,
    *,
    python_executable: str | None = None,
) -> tuple[str, list[str]]:
    command = python_executable or (
        GENERIC_PYTHON_PLACEHOLDER if repo_root is None else sys.executable
    )
    args = ["-m", "decodifier.cli", "mcp-server"]
    if repo_root is not None:
        root = Path(repo_root).resolve()
        args.extend(["--path", str(root)])
    return command, args


def _quoted_command(command: str, args: Sequence[str]) -> str:
    return shlex.join([command, *args])


def _agent_instruction(server_name: str) -> str:
    return (
        f"Use the `{server_name}` MCP server for code retrieval before broad file search. "
        "Start with `search_symbols`, then `get_context_read_plan`, and only call "
        "`materialize_context` when bounded source context is required."
    )


def render_codex_adapter(
    repo_root: str | Path | None = None,
    *,
    server_name: str = "decodifier",
    python_executable: str | None = None,
) -> str:
    command, args = _server_command(repo_root, python_executable=python_executable)
    install_command = f"codex mcp add {shlex.quote(server_name)} -- {_quoted_command(command, args)}"
    config_lines = [
        f"[mcp_servers.{server_name}]",
        f'command = {json.dumps(command)}',
        f"args = {json.dumps(args)}",
    ]
    sections = [
        "Codex MCP Adapter",
        "",
        "Install command:",
        install_command,
        "",
        "~/.codex/config.toml:",
        "\n".join(config_lines),
        "",
        "Note:",
        (
            "Run Codex from the repo root you want DeCodifier to index."
            if repo_root is None
            else "This config is pinned to a specific local repo path."
        ),
        "",
        "Suggested AGENTS.md instruction:",
        _agent_instruction(server_name),
    ]
    return "\n".join(sections) + "\n"


def render_claude_code_adapter(
    repo_root: str | Path | None = None,
    *,
    server_name: str = "decodifier",
    scope: str = "project",
    python_executable: str | None = None,
) -> str:
    command, args = _server_command(repo_root, python_executable=python_executable)
    install_command = (
        f"claude mcp add {shlex.quote(server_name)} --transport stdio "
        f"--scope {shlex.quote(scope)} -- {_quoted_command(command, args)}"
    )
    project_config = {
        "mcpServers": {
            server_name: {
                "command": command,
                "args": args,
            }
        }
    }
    sections = [
        "Claude Code MCP Adapter",
        "",
        "Install command:",
        install_command,
        "",
        ".mcp.json:",
        json.dumps(project_config, indent=2, sort_keys=True),
        "",
        "Note:",
        (
            "Run Claude Code from the repo root you want DeCodifier to index."
            if repo_root is None
            else "This config is pinned to a specific local repo path."
        ),
        "",
        "Suggested CLAUDE.md instruction:",
        _agent_instruction(server_name),
    ]
    return "\n".join(sections) + "\n"
