from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .adapters import render_claude_code_adapter, render_codex_adapter
from .benchmark import (
    DEFAULT_BENCHMARK_MARKDOWN_PATH,
    DEFAULT_BENCHMARK_SNAPSHOT_PATH,
    DEFAULT_FIXTURE_REPOS_ROOT,
    DEFAULT_ENGINES,
    DEFAULT_TOKEN_BUDGETS,
    render_fixture_benchmark_markdown,
    run_fixture_benchmark,
)
from .mcp_server import run_stdio_mcp_server
from .retrieval import get_context_read_plan, materialize_context, search_symbols
from .tool_server import run_stdio_tool_server


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="decodifier", description="DeCodifier local retrieval CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    query_parser = subparsers.add_parser("query", help="Search for the most relevant symbols in a repo")
    query_parser.add_argument("query", help="Natural-language query")
    query_parser.add_argument("--path", default=".", help="Repo root to search")
    query_parser.add_argument("--max-symbols", type=int, default=5, help="Maximum symbols to return")
    query_parser.add_argument("--max-tokens", type=int, default=800, help="Context token budget")
    query_parser.add_argument("--max-lines", type=int, default=120, help="Context line budget")
    query_parser.add_argument(
        "--materialize",
        action="store_true",
        help="Render the planned context after listing symbols",
    )
    query_parser.add_argument(
        "--debug",
        action="store_true",
        help="Print retrieval rationale and debug metadata for each symbol hit",
    )

    benchmark_parser = subparsers.add_parser("benchmark", help="Run retrieval benchmarks against fixture repos")
    benchmark_parser.add_argument(
        "--fixtures-root",
        default=str(DEFAULT_FIXTURE_REPOS_ROOT),
        help="Path to the retrieval fixture repos directory",
    )
    benchmark_parser.add_argument(
        "--engines",
        nargs="+",
        default=list(DEFAULT_ENGINES),
        choices=list(DEFAULT_ENGINES),
        help="Benchmark engines to run",
    )
    benchmark_parser.add_argument("--max-symbols", type=int, default=3, help="Maximum symbols to return per query")
    benchmark_parser.add_argument("--max-lines", type=int, default=80, help="Context line budget")
    benchmark_parser.add_argument(
        "--token-budgets",
        nargs="+",
        type=int,
        default=list(DEFAULT_TOKEN_BUDGETS),
        help="Context token budgets to benchmark",
    )
    benchmark_parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Single context token budget to benchmark instead of the default budget set",
    )
    benchmark_parser.add_argument(
        "--snapshot-out",
        default=str(DEFAULT_BENCHMARK_SNAPSHOT_PATH),
        help="Path to write the JSON benchmark snapshot",
    )
    benchmark_parser.add_argument(
        "--markdown-out",
        default=str(DEFAULT_BENCHMARK_MARKDOWN_PATH),
        help="Path to write the markdown benchmark report",
    )

    tool_server_parser = subparsers.add_parser(
        "tool-server",
        help="Run a stdio JSON tool server for local agent integration",
    )
    tool_server_parser.add_argument("--path", default=".", help="Repo root to serve tools against")

    mcp_server_parser = subparsers.add_parser(
        "mcp-server",
        help="Run a stdio MCP server for Codex, Claude Code, and other MCP clients",
    )
    mcp_server_parser.add_argument("--path", default=None, help="Repo root to serve tools against")

    adapter_parser = subparsers.add_parser(
        "adapter",
        help="Print MCP adapter snippets for agent clients",
    )
    adapter_parser.add_argument("target", choices=["codex", "claude-code"], help="Adapter target")
    adapter_parser.add_argument("--path", default=None, help="Repo root to serve tools against")
    adapter_parser.add_argument("--name", default="decodifier", help="MCP server name")
    adapter_parser.add_argument(
        "--scope",
        choices=["local", "project", "user"],
        default="project",
        help="Claude Code MCP scope",
    )
    adapter_parser.add_argument(
        "--python",
        default=None,
        help="Python executable used to launch the MCP server",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "query":
        repo_root = Path(args.path).resolve()
        symbols = search_symbols(repo_root, args.query, max_symbols=args.max_symbols)
        for symbol in symbols:
            print(symbol["symbol"])
            print(f"{symbol['path']}:{symbol['start_line']}-{symbol['end_line']}")
            if args.debug:
                surfaces = symbol.get("behavior_surfaces") or []
                if surfaces:
                    print(f"  surfaces: {', '.join(surfaces)}")
                for reason in symbol.get("rationale") or []:
                    print(f"  why: {reason}")
                debug = symbol.get("debug") or {}
                if debug:
                    print(f"  debug: {json.dumps(debug, sort_keys=True)}")

        if args.materialize:
            plan = get_context_read_plan(
                repo_root,
                args.query,
                max_symbols=args.max_symbols,
                max_tokens=args.max_tokens,
                max_lines=args.max_lines,
            )
            context = materialize_context(
                repo_root,
                plan,
                max_tokens=args.max_tokens,
                max_symbols=args.max_symbols,
                max_lines=args.max_lines,
            )
            if context["content"]:
                print()
                print(context["content"])
        return 0

    if args.command == "benchmark":
        result = run_fixture_benchmark(
            fixtures_root=args.fixtures_root,
            engines=args.engines,
            max_symbols=args.max_symbols,
            token_budgets=args.token_budgets,
            max_tokens=args.max_tokens,
            max_lines=args.max_lines,
        )
        Path(args.snapshot_out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        markdown = render_fixture_benchmark_markdown(result)
        Path(args.markdown_out).write_text(markdown, encoding="utf-8")
        print(markdown, end="")
        return 0

    if args.command == "tool-server":
        return run_stdio_tool_server(Path(args.path).resolve())

    if args.command == "mcp-server":
        repo_root = Path(args.path).resolve() if args.path else Path.cwd().resolve()
        return run_stdio_mcp_server(repo_root)

    if args.command == "adapter":
        repo_root = Path(args.path).resolve() if args.path else None
        if args.target == "codex":
            print(
                render_codex_adapter(
                    repo_root,
                    server_name=args.name,
                    python_executable=args.python,
                ),
                end="",
            )
            return 0
        if args.target == "claude-code":
            print(
                render_claude_code_adapter(
                    repo_root,
                    server_name=args.name,
                    scope=args.scope,
                    python_executable=args.python,
                ),
                end="",
            )
            return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
