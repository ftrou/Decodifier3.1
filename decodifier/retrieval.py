from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

DEFAULT_IGNORE = (
    ".git",
    ".decodifier",
    "node_modules",
    "dist",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
)

SUPPORTED_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".rs"}
CONTROL_KEYWORDS = {"if", "for", "while", "switch", "catch", "return"}
SUPPRESSED_DIR_PARTS = {"tests", "test", "benchmarks", "benchmark", "fixtures", "__snapshots__", "__mocks__"}
LOW_SIGNAL_PATH_PARTS = {"generated", "examples", "example", "samples", "sample", "mocks", "mock"}
LOW_SIGNAL_FILE_STEMS = {"conftest"}
AUTH_QUERY_HINTS = {"authentication", "token", "login", "session", "refresh", "scope", "validate", "expire"}
AUTH_PATH_HINTS = {"auth", "authentication", "security", "session", "token", "permission", "permissions", "scope", "login"}
CONTROL_FLOW_PATH_HINTS = {"controller", "service", "handler", "middleware", "guard", "policy", "dep", "route", "router"}
CALLER_PROMOTION_TERMS = {"check", "checked", "permission", "permissions", "scope", "trace", "flow", "caller", "callers", "called", "calls", "usage", "used"}
PASSWORD_RESET_TOKENS = {"reset", "recovery", "email"}
ACCESS_TOKEN_TOKENS = {"jwt", "decode", "oauth2", "credential", "current", "user", "forbidden", "403", "invalid"}
PERMISSION_GUARD_TOKENS = {"403", "forbidden", "superuser", "owner", "privilege"}
SETTINGS_TOKENS = {"secret", "setting", "default", "config"}

PY_CLASS_RE = re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\b")
PY_DEF_RE = re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
FASTAPI_ROUTE_DECORATOR_RE = re.compile(r"^\s*@(?:\w+\.)?(?:router|app)\.(?:get|post|put|delete|patch|options|head|api_route)\b")
FASTAPI_DEPENDS_RE = re.compile(r"\bDepends\(\s*([A-Za-z_][A-Za-z0-9_]*)?\s*\)")
FASTAPI_SECURITY_RE = re.compile(r"\bSecurity\(\s*([A-Za-z_][A-Za-z0-9_]*)")
FASTAPI_ANNOTATED_ALIAS_RE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*Annotated\[.*?(?:Depends|Security)\(\s*([A-Za-z_][A-Za-z0-9_]*)?\s*\)",
)
PY_SIGNATURE_ANNOTATION_RE = re.compile(r":\s*([A-Za-z_][A-Za-z0-9_]*)")
JS_CLASS_RE = re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)\b")
JS_FUNCTION_RE = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
JS_ARROW_RE = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_][A-Za-z0-9_]*)\s*=>"
)
JS_METHOD_RE = re.compile(
    r"^\s*(?:public|private|protected\s+)?(?:static\s+)?(?:async\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\([^;]*\)\s*(?::\s*[^={]+)?\{"
)
JAVA_CLASS_RE = re.compile(r"^\s*(?:public\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)\b")
JAVA_METHOD_RE = re.compile(
    r"^\s*(?:public|private|protected)\s+(?:static\s+)?(?:final\s+)?[A-Za-z0-9_<>\[\], ?]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("
)
RUST_STRUCT_RE = re.compile(r"^\s*(?:pub\s+)?struct\s+([A-Za-z_][A-Za-z0-9_]*)\b")
RUST_IMPL_RE = re.compile(r"^\s*impl\s+([A-Za-z_][A-Za-z0-9_]*)\b")
RUST_FN_RE = re.compile(r"^\s*(?:pub\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
NON_WORD_RE = re.compile(r"[^A-Za-z0-9]+")
CALL_RE = re.compile(r"(?:\b(?:self|this|super)\.)?(?:[A-Za-z_][A-Za-z0-9_]*\.)*([A-Za-z_][A-Za-z0-9_]*)\s*\(")
STRING_LITERAL_RE = re.compile(r"(\"\"\".*?\"\"\"|'''.*?'''|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)", re.DOTALL)

CANONICAL_TOKENS = {
    "validation": "validate",
    "validated": "validate",
    "validator": "validate",
    "validators": "validate",
    "verification": "verify",
    "verified": "verify",
    "check": "validate",
    "checks": "validate",
    "checked": "validate",
    "checking": "validate",
    "auth": "authentication",
    "authenticate": "authentication",
    "authenticated": "authentication",
    "authentication": "authentication",
    "authorise": "scope",
    "authorize": "scope",
    "authorized": "scope",
    "authorization": "scope",
    "permission": "scope",
    "permissions": "scope",
    "scope": "scope",
    "scopes": "scope",
    "expiry": "expire",
    "expiration": "expire",
    "expired": "expire",
    "expires": "expire",
    "handle": "handle",
    "handled": "handle",
    "handling": "handle",
    "generate": "generate",
    "generated": "generate",
    "generates": "generate",
    "issue": "generate",
    "issued": "generate",
    "login": "login",
    "logins": "login",
    "signin": "login",
    "session": "session",
    "sessions": "session",
    "refresh": "refresh",
    "token": "token",
    "tokens": "token",
    "enforced": "enforce",
    "enforcement": "enforce",
}

QUERY_TOKEN_ALIASES = {
    "authentication": {"authentication", "authenticate", "auth", "login"},
    "enforce": {"enforce", "validate", "verify", "decode", "assert", "require", "check"},
    "expire": {"expire", "expired", "timeout"},
    "generate": {"generate", "issue", "create", "encode"},
    "login": {"login", "signin", "authenticate", "credential"},
    "refresh": {"refresh", "renew"},
    "scope": {"scope", "permission", "authorize", "allow"},
    "session": {"session", "cookie"},
    "token": {"token", "jwt", "bearer"},
    "validate": {"validate", "verify", "decode", "enforce", "check", "assert", "require", "has"},
}

QUERY_STOPWORDS = {"where", "is", "are", "the", "a", "an", "to", "and", "of"}
NOISE_HINTS = {"banner", "notice", "summary", "label", "copy", "render", "build"}
CALL_STOPWORDS = CONTROL_KEYWORDS | {"class", "def", "fn", "function", "new", "raise", "await", "match", "assert"}


def _matches_ignore(rel: Path, patterns: Iterable[str]) -> bool:
    rel_str = rel.as_posix()
    parts = rel_str.split("/")
    for pattern in patterns:
        normalized = pattern.strip().lstrip("./")
        if not normalized:
            continue
        if normalized.endswith("/"):
            normalized = normalized[:-1]
        if rel_str == normalized or rel_str.startswith(f"{normalized}/"):
            return True
        if normalized in parts:
            return True
    return False


def _is_suppressed_file(rel: Path) -> bool:
    if any(part.lower() in SUPPRESSED_DIR_PARTS for part in rel.parts[:-1]):
        return True

    name = rel.name.lower()
    stem = rel.stem.lower()
    if stem in LOW_SIGNAL_FILE_STEMS:
        return True
    if stem.startswith("test_") or stem.endswith("_test"):
        return True
    if "benchmark" in stem:
        return True
    if name.endswith(".snap"):
        return True
    return False


def _split_identifier(token: str) -> List[str]:
    camel_split = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", token)
    normalized = NON_WORD_RE.sub(" ", camel_split.replace("_", " "))
    return [part for part in normalized.lower().split() if part]


def _canonicalize(token: str) -> str:
    raw = token.lower().strip()
    if raw in CANONICAL_TOKENS:
        return CANONICAL_TOKENS[raw]
    if raw.endswith("ies") and len(raw) > 4:
        raw = raw[:-3] + "y"
    elif raw.endswith("es") and len(raw) > 4:
        raw = raw[:-2]
    elif raw.endswith("s") and len(raw) > 3:
        raw = raw[:-1]
    if raw.endswith("ing") and len(raw) > 5:
        raw = raw[:-3]
    elif raw.endswith("ed") and len(raw) > 4:
        raw = raw[:-2]
    return CANONICAL_TOKENS.get(raw, raw)


def _tokenize_text(text: str) -> List[str]:
    tokens: List[str] = []
    for match in TOKEN_RE.findall(text):
        for part in _split_identifier(match):
            canonical = _canonicalize(part)
            if canonical and canonical not in QUERY_STOPWORDS:
                tokens.append(canonical)
    return tokens


def _tokenize_code(text: str) -> List[str]:
    return _tokenize_text(STRING_LITERAL_RE.sub(" ", text))


def _approx_token_count(text: str) -> int:
    return len(re.findall(r"\w+|[^\w\s]", text))


def _language_for_suffix(suffix: str) -> str:
    return {
        ".py": "python",
        ".ts": "ts",
        ".tsx": "tsx",
        ".js": "js",
        ".jsx": "jsx",
        ".java": "java",
        ".rs": "rust",
    }.get(suffix, "text")


def _iter_code_files(root: Path, ignore: Iterable[str]) -> Iterable[Path]:
    ignore_patterns = tuple(dict.fromkeys([*DEFAULT_IGNORE, *list(ignore)]))
    for dirpath, dirnames, filenames in os.walk(root):
        current_dir = Path(dirpath)
        rel_dir = current_dir.relative_to(root)

        pruned: List[str] = []
        for dirname in dirnames:
            rel = (current_dir / dirname).relative_to(root)
            if any(part.startswith(".") for part in rel.parts):
                continue
            if any(part.lower() in SUPPRESSED_DIR_PARTS for part in rel.parts):
                continue
            if _matches_ignore(rel, ignore_patterns):
                continue
            pruned.append(dirname)
        dirnames[:] = sorted(pruned)

        if rel_dir != Path(".") and any(part.startswith(".") for part in rel_dir.parts):
            continue
        if rel_dir != Path(".") and _matches_ignore(rel_dir, ignore_patterns):
            continue

        for filename in sorted(filenames):
            path = current_dir / filename
            if path.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            rel = path.relative_to(root)
            if any(part.startswith(".") for part in rel.parts):
                continue
            if _is_suppressed_file(rel):
                continue
            if _matches_ignore(rel, ignore_patterns):
                continue
            yield path


def _make_symbol(
    *,
    rel_path: str,
    name: str,
    kind: str,
    start_line: int,
    total_lines: int,
    container: Optional[str] = None,
) -> Dict[str, Any]:
    symbol_name = f"{container}.{name}" if container and kind in {"method", "function"} else name
    return {
        "symbol": symbol_name,
        "name": name,
        "container": container,
        "kind": kind,
        "path": rel_path,
        "start_line": start_line,
        "end_line": min(total_lines, start_line + 12),
    }


def _extract_symbols_from_file(path: Path, root: Path) -> List[Dict[str, Any]]:
    rel_path = path.relative_to(root).as_posix()
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    suffix = path.suffix.lower()
    symbols: List[Dict[str, Any]] = []

    if suffix == ".py":
        class_stack: List[tuple[str, int]] = []
        pending_decorators: List[str] = []
        for line_no, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("@"):
                pending_decorators.append(stripped)
                continue
            indent = len(line) - len(line.lstrip(" "))
            while class_stack and indent <= class_stack[-1][1]:
                class_stack.pop()

            class_match = PY_CLASS_RE.match(line)
            if class_match:
                name = class_match.group(1)
                symbol = _make_symbol(
                    rel_path=rel_path,
                    name=name,
                    kind="class",
                    start_line=line_no,
                    total_lines=len(lines),
                )
                symbol["decorators"] = list(pending_decorators)
                symbols.append(symbol)
                class_stack.append((name, indent))
                pending_decorators = []
                continue

            def_match = PY_DEF_RE.match(line)
            if def_match:
                name = def_match.group(1)
                container = class_stack[-1][0] if class_stack else None
                symbol = _make_symbol(
                    rel_path=rel_path,
                    name=name,
                    kind="method" if container else "function",
                    start_line=line_no,
                    total_lines=len(lines),
                    container=container,
                )
                symbol["decorators"] = list(pending_decorators)
                symbols.append(symbol)
                pending_decorators = []
                continue
            pending_decorators = []
        return _finalize_symbol_ranges(symbols, total_lines=len(lines))

    class_stack: List[tuple[str, int]] = []
    brace_depth = 0
    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()

        class_match = None
        fn_match = None
        kind = "class"
        if suffix in {".ts", ".tsx", ".js", ".jsx"}:
            class_match = JS_CLASS_RE.match(line)
            fn_match = JS_FUNCTION_RE.match(line) or JS_ARROW_RE.match(line) or JS_METHOD_RE.match(line)
        elif suffix == ".java":
            class_match = JAVA_CLASS_RE.match(line)
            fn_match = JAVA_METHOD_RE.match(line)
        elif suffix == ".rs":
            class_match = RUST_IMPL_RE.match(line) or RUST_STRUCT_RE.match(line)
            fn_match = RUST_FN_RE.match(line)
            kind = "impl" if RUST_IMPL_RE.match(line) else "class"

        if class_match:
            name = class_match.group(1)
            symbols.append(
                _make_symbol(
                    rel_path=rel_path,
                    name=name,
                    kind=kind,
                    start_line=line_no,
                    total_lines=len(lines),
                )
            )
            class_stack.append((name, brace_depth))
        elif fn_match:
            name = fn_match.group(1)
            if name not in CONTROL_KEYWORDS:
                container = class_stack[-1][0] if class_stack else None
                symbols.append(
                    _make_symbol(
                        rel_path=rel_path,
                        name=name,
                        kind="method" if container else "function",
                        start_line=line_no,
                        total_lines=len(lines),
                        container=container,
                    )
                )

        brace_depth += line.count("{") - line.count("}")
        while class_stack and brace_depth <= class_stack[-1][1]:
            class_stack.pop()

        if suffix in {".ts", ".tsx", ".js", ".jsx"} and stripped == "}":
            while class_stack and brace_depth <= class_stack[-1][1]:
                class_stack.pop()

    return _finalize_symbol_ranges(symbols, total_lines=len(lines))


def _finalize_symbol_ranges(symbols: List[Dict[str, Any]], *, total_lines: int) -> List[Dict[str, Any]]:
    ordered = sorted(symbols, key=lambda item: (item["start_line"], item["symbol"]))
    for index, symbol in enumerate(ordered):
        next_start = total_lines + 1
        if index + 1 < len(ordered):
            next_start = ordered[index + 1]["start_line"]
        capped_end = min(symbol["end_line"], total_lines, max(symbol["start_line"], next_start - 1))
        symbol["end_line"] = capped_end
    return ordered


def _collect_symbols(root: Path, ignore: Iterable[str]) -> List[Dict[str, Any]]:
    symbols: List[Dict[str, Any]] = []
    for path in _iter_code_files(root, ignore):
        symbols.extend(_extract_symbols_from_file(path, root))
    symbols.sort(key=lambda item: (item["path"], item["start_line"], item["symbol"]))
    for symbol in symbols:
        if symbol["kind"] not in {"method", "function"}:
            symbol["calls"] = []
            symbol["call_edges"] = []
            symbol["caller_edges"] = []
            continue
        snippet = _symbol_snippet(root, symbol)
        symbol["calls"] = _extract_call_names(snippet, symbol_name=symbol["name"])
        symbol["call_edges"] = []
        symbol["caller_edges"] = []
    _attach_call_graph(symbols)
    _attach_fastapi_framework_edges(root, symbols)
    return symbols


def _directory_scope(path: str) -> str:
    parent = Path(path).parent
    if parent == Path("."):
        return ""
    return parent.as_posix()


def _resolve_call_target(
    source: Dict[str, Any],
    call_name: str,
    *,
    repo_name_index: Dict[str, List[Dict[str, Any]]],
) -> Optional[Dict[str, Any]]:
    candidates = repo_name_index.get(call_name, [])
    if not candidates:
        return None

    source_container = source.get("container")
    source_path = source["path"]
    source_directory = _directory_scope(source_path)

    same_container = [
        candidate
        for candidate in candidates
        if candidate["path"] == source_path and candidate.get("container") == source_container
    ]
    if len(same_container) == 1:
        return {"target": same_container[0], "confidence": 1.0}

    same_file = [candidate for candidate in candidates if candidate["path"] == source_path]
    if len(same_file) == 1:
        return {"target": same_file[0], "confidence": 0.95}

    same_directory = [
        candidate for candidate in candidates if _directory_scope(candidate["path"]) == source_directory
    ]
    if len(same_directory) == 1:
        return {"target": same_directory[0], "confidence": 0.85}

    if len(candidates) == 1:
        return {"target": candidates[0], "confidence": 0.7}

    return None


def _attach_call_graph(symbols: List[Dict[str, Any]]) -> None:
    methods = [symbol for symbol in symbols if symbol["kind"] in {"method", "function"}]
    repo_name_index: Dict[str, List[Dict[str, Any]]] = {}
    by_key = {_symbol_key(symbol): symbol for symbol in methods}
    for symbol in methods:
        repo_name_index.setdefault(symbol["name"], []).append(symbol)

    for symbol in methods:
        resolved_targets: set[tuple[str, str, int]] = set()
        for call_name in symbol.get("calls", []):
            resolved = _resolve_call_target(symbol, call_name, repo_name_index=repo_name_index)
            if not resolved:
                continue
            target = resolved["target"]
            target_key = _symbol_key(target)
            if target_key == _symbol_key(symbol) or target_key in resolved_targets:
                continue
            resolved_targets.add(target_key)
            symbol["call_edges"].append({"key": target_key, "confidence": resolved["confidence"]})

    for symbol in methods:
        source_key = _symbol_key(symbol)
        for edge in symbol.get("call_edges", []):
            target = by_key.get(edge["key"])
            if target is None:
                continue
            target["caller_edges"].append({"key": source_key, "confidence": edge["confidence"]})


def _python_signature_text(snippet: str) -> str:
    header_lines: List[str] = []
    paren_depth = 0
    for line in snippet.splitlines():
        stripped = line.strip()
        if not stripped:
            if header_lines:
                break
            continue
        header_lines.append(stripped)
        paren_depth += stripped.count("(") - stripped.count(")")
        if stripped.endswith(":") and paren_depth <= 0:
            break
    return " ".join(header_lines)


def _extract_fastapi_aliases(lines: List[str]) -> Dict[str, str]:
    aliases: Dict[str, str] = {}
    for line in lines:
        match = FASTAPI_ANNOTATED_ALIAS_RE.match(line)
        if not match:
            continue
        alias_name = match.group(1)
        target_name = match.group(2)
        if target_name:
            aliases[alias_name] = target_name
    return aliases


def _extend_fastapi_dependency_names(text: str, names: set[str]) -> None:
    for pattern in (FASTAPI_DEPENDS_RE, FASTAPI_SECURITY_RE):
        for match in pattern.findall(text):
            if match:
                names.add(match)


def _append_framework_edge(source: Dict[str, Any], target: Dict[str, Any], *, confidence: float) -> None:
    target_key = _symbol_key(target)
    if any(edge["key"] == target_key for edge in source.get("call_edges", [])):
        return
    source.setdefault("call_edges", []).append({"key": target_key, "confidence": confidence, "kind": "framework"})
    target.setdefault("caller_edges", []).append(
        {"key": _symbol_key(source), "confidence": confidence, "kind": "framework"}
    )


def _attach_fastapi_framework_edges(root: Path, symbols: List[Dict[str, Any]]) -> None:
    method_symbols = [symbol for symbol in symbols if symbol["kind"] in {"method", "function"} and symbol["path"].endswith(".py")]
    if not method_symbols:
        return

    symbols_by_path: Dict[str, List[Dict[str, Any]]] = {}
    local_alias_maps: Dict[str, Dict[str, str]] = {}
    global_alias_targets: Dict[str, set[str]] = {}
    repo_name_index: Dict[str, List[Dict[str, Any]]] = {}

    for symbol in method_symbols:
        symbols_by_path.setdefault(symbol["path"], []).append(symbol)
        repo_name_index.setdefault(symbol["name"], []).append(symbol)

    for rel_path in symbols_by_path:
        lines = (root / rel_path).read_text(encoding="utf-8", errors="ignore").splitlines()
        alias_map = _extract_fastapi_aliases(lines)
        local_alias_maps[rel_path] = alias_map
        for alias_name, target_name in alias_map.items():
            global_alias_targets.setdefault(alias_name, set()).add(target_name)

    global_alias_map = {
        alias_name: next(iter(targets))
        for alias_name, targets in global_alias_targets.items()
        if len(targets) == 1
    }

    referenced_dependency_names: set[str] = set()
    for symbol in method_symbols:
        symbol["framework_roles"] = list(symbol.get("framework_roles", []))
        symbol["framework_dependency_names"] = []
        decorators = symbol.get("decorators", [])
        signature_text = _python_signature_text(_symbol_snippet(root, symbol))
        dependency_names: set[str] = set()
        _extend_fastapi_dependency_names(signature_text, dependency_names)
        _extend_fastapi_dependency_names(" ".join(decorators), dependency_names)

        alias_map = local_alias_maps.get(symbol["path"], {})
        for annotation_name in PY_SIGNATURE_ANNOTATION_RE.findall(signature_text):
            target_name = alias_map.get(annotation_name) or global_alias_map.get(annotation_name)
            if target_name:
                dependency_names.add(target_name)

        if any(FASTAPI_ROUTE_DECORATOR_RE.match(decorator) for decorator in decorators):
            symbol["framework_roles"].append("fastapi_route")
        if dependency_names:
            symbol["framework_dependency_names"] = sorted(dependency_names)
            referenced_dependency_names.update(dependency_names)

    for symbol in method_symbols:
        roles = set(symbol.get("framework_roles", []))
        if symbol["name"] in referenced_dependency_names:
            roles.add("fastapi_dependency")
            snippet_tokens = set(_tokenize_code(_symbol_snippet(root, symbol)))
            if {"jwt", "decode"} & snippet_tokens or {"httpexception", "forbidden", "privilege"} & snippet_tokens:
                roles.add("fastapi_guard")
        symbol["framework_roles"] = sorted(roles)

    for symbol in method_symbols:
        for dependency_name in symbol.get("framework_dependency_names", []):
            resolved = _resolve_call_target(symbol, dependency_name, repo_name_index=repo_name_index)
            if not resolved:
                continue
            _append_framework_edge(symbol, resolved["target"], confidence=max(0.8, resolved["confidence"]))


def _symbol_snippet(root: Path, symbol: Dict[str, Any]) -> str:
    cached = symbol.get("_snippet")
    if isinstance(cached, str):
        return cached

    path = root / symbol["path"]
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    start = max(1, symbol["start_line"])
    end = min(len(lines), symbol["end_line"])
    snippet = "\n".join(lines[start - 1 : end])
    symbol["_snippet"] = snippet
    return snippet


def _snippet_tokens(root: Path, symbol: Dict[str, Any]) -> List[str]:
    cached = symbol.get("_snippet_tokens")
    if isinstance(cached, list):
        return cached

    tokens = _tokenize_code(_symbol_snippet(root, symbol))
    symbol["_snippet_tokens"] = tokens
    return tokens


def _extract_call_names(snippet: str, *, symbol_name: str) -> List[str]:
    call_names: set[str] = set()
    for line_index, line in enumerate(snippet.splitlines()):
        stripped = line.strip()
        if line_index == 0 or not stripped:
            continue
        if stripped.startswith(("#", "//", "/*", "*")):
            continue
        for name in CALL_RE.findall(stripped):
            if name == symbol_name or name in CALL_STOPWORDS:
                continue
            if name[:1].isupper():
                continue
            call_names.add(name)
    return sorted(call_names)


def _query_steps(query: str) -> List[str]:
    normalized = query.replace("→", "->").strip()
    if normalized.lower().startswith("trace "):
        normalized = normalized[6:].strip()
    if "->" not in normalized:
        return [query]
    return [part.strip() for part in normalized.split("->") if part.strip()]


def _path_tokens(path: str) -> set[str]:
    return set(_tokenize_text(path))


def _required_coverage(query_tokens: set[str]) -> int:
    if not query_tokens:
        return 0
    return min(len(query_tokens), 3)


def _query_alias_group(token: str) -> set[str]:
    return QUERY_TOKEN_ALIASES.get(token, {token})


def _count_query_token_hits(query_tokens: set[str], candidate_tokens: set[str]) -> int:
    return sum(1 for token in query_tokens if _query_alias_group(token) & candidate_tokens)


def _is_trace_query(query: str) -> bool:
    normalized = query.replace("→", "->").strip().lower()
    return normalized.startswith("trace ") or "->" in normalized


def _should_promote_callers(query: str) -> bool:
    if _is_trace_query(query):
        return False
    lower = query.lower()
    return any(term in lower for term in CALLER_PROMOTION_TERMS)


def _score_symbol(root: Path, query: str, symbol: Dict[str, Any]) -> Dict[str, Any]:
    query_tokens = set(_tokenize_text(query))
    if not query_tokens:
        return {"score": 0.0, "coverage_count": 0, "coverage_ratio": 0.0}

    name_tokens = set(_tokenize_text(symbol["symbol"]))
    path_tokens = _path_tokens(symbol["path"])
    snippet_tokens = set(_snippet_tokens(root, symbol))
    combined_tokens = name_tokens | path_tokens | snippet_tokens
    domain_hits = len(combined_tokens & (AUTH_QUERY_HINTS | AUTH_PATH_HINTS))
    framework_roles = set(symbol.get("framework_roles", []))
    auth_enforcement_query = (
        ("token" in query_tokens or "authentication" in query_tokens or "session" in query_tokens)
        and ("validate" in query_tokens or "enforce" in query_tokens)
    )
    token_guard_signal = bool({"token", "jwt", "decode", "credential", "oauth2"} & combined_tokens)
    if framework_roles & {"fastapi_route", "fastapi_dependency", "fastapi_guard"}:
        domain_hits += 2

    name_hits = _count_query_token_hits(query_tokens, name_tokens)
    path_hits = _count_query_token_hits(query_tokens, path_tokens)
    snippet_hits = _count_query_token_hits(query_tokens, snippet_tokens)
    coverage_count = _count_query_token_hits(query_tokens, combined_tokens)
    coverage_ratio = coverage_count / max(len(query_tokens), 1)
    score = float(name_hits * 10 + path_hits * 1.5 + snippet_hits * 2 + coverage_count * 4)

    if coverage_count == len(query_tokens) and name_hits == len(query_tokens):
        score += 12.0
    if coverage_count == len(query_tokens):
        score += 10.0
    if "enforce" in query_tokens and "enforce" in name_tokens:
        score += 8.0
    if symbol["kind"] == "method":
        score += 4.0
    if symbol["kind"] in {"class", "impl"}:
        score -= 3.0
    if symbol.get("container"):
        score += 1.0
    if query_tokens & AUTH_QUERY_HINTS:
        score += 2.0 * len(path_tokens & AUTH_PATH_HINTS)
        score += 1.5 * len(path_tokens & CONTROL_FLOW_PATH_HINTS)
    if {"validate", "enforce"} & query_tokens and {"raise", "decode", "verify"} & snippet_tokens:
        score += 6.0
    if {"token", "validate"} <= query_tokens and {"jwt", "decode"} <= snippet_tokens:
        score += 8.0
        if snippet_tokens & ACCESS_TOKEN_TOKENS:
            score += 6.0
        if {"current", "user"} & combined_tokens and {"httpexception", "forbidden"} & snippet_tokens:
            score += 12.0
        if "enforce" in query_tokens:
            coverage_count = max(coverage_count, min(len(query_tokens), 3))
    if "scope" in query_tokens and {"scope", "permission"} & snippet_tokens:
        score += 6.0
    if "scope" in query_tokens and {"httpexception", "raise", "forbidden"} & snippet_tokens and {"superuser", "owner", "privilege"} & snippet_tokens:
        coverage_count = max(coverage_count, min(len(query_tokens), 2))
        score += 14.0
    if "scope" in query_tokens and {"superuser", "owner", "privilege"} & combined_tokens and {"httpexception", "raise"} & snippet_tokens:
        score += 4.0
    if {"session", "expire"} & query_tokens and {"session", "expire", "timeout"} & snippet_tokens:
        score += 5.0
    if "login" in query_tokens and {"password", "credential", "verify", "hash"} & snippet_tokens:
        score += 4.0
    if "login" in query_tokens and "login" in name_tokens:
        score += 3.0
    if {"refresh", "token"} <= query_tokens and {"refresh", "issue", "generate"} & snippet_tokens:
        score += 4.0
    if not query_tokens & PASSWORD_RESET_TOKENS and combined_tokens & PASSWORD_RESET_TOKENS:
        score -= 30.0
    if query_tokens & AUTH_QUERY_HINTS and combined_tokens & SETTINGS_TOKENS and not {"jwt", "decode", "oauth2"} & snippet_tokens:
        score -= 12.0
    if (name_tokens | path_tokens) & NOISE_HINTS:
        score -= 4.0
    if path_tokens & LOW_SIGNAL_PATH_PARTS:
        score -= 6.0
    if "fastapi_route" in framework_roles:
        if "scope" in query_tokens:
            score += 8.0
            if {"httpexception", "forbidden", "owner", "superuser"} & snippet_tokens:
                score += 6.0
                coverage_count = max(coverage_count, min(len(query_tokens), 2))
        if "login" in query_tokens:
            score += 5.0
        if auth_enforcement_query and symbol.get("framework_dependency_names"):
            score += 3.0
    if "fastapi_dependency" in framework_roles:
        if auth_enforcement_query and token_guard_signal:
            score += 9.0
            if symbol.get("caller_edges"):
                score += 5.0
        if "scope" in query_tokens and {"current", "user", "superuser"} & combined_tokens:
            score += 4.0
    if "fastapi_guard" in framework_roles:
        if auth_enforcement_query and token_guard_signal:
            score += 8.0
            coverage_count = max(coverage_count, min(len(query_tokens), 3))
            if symbol.get("caller_edges"):
                score += 8.0
        if auth_enforcement_query and "enforce" in query_tokens and token_guard_signal:
            score += 10.0
        if "scope" in query_tokens:
            score += 5.0

    return {
        "score": round(score, 2),
        "coverage_count": coverage_count,
        "coverage_ratio": round(coverage_ratio, 4),
        "name_hits": name_hits,
        "path_hits": path_hits,
        "snippet_hits": snippet_hits,
        "domain_hits": domain_hits,
    }


def _passes_confidence(scored_symbol: Dict[str, Any], query_tokens: set[str]) -> bool:
    required_coverage = _required_coverage(query_tokens)
    if scored_symbol["coverage_count"] < required_coverage:
        return False
    if scored_symbol["score"] < 12.0:
        return False
    if query_tokens & AUTH_QUERY_HINTS and scored_symbol.get("domain_hits", 0) == 0:
        return False
    return True


def _public_symbol(scored_symbol: Dict[str, Any]) -> Dict[str, Any]:
    public = {
        "symbol": scored_symbol["symbol"],
        "name": scored_symbol["name"],
        "kind": scored_symbol["kind"],
        "path": scored_symbol["path"],
        "start_line": scored_symbol["start_line"],
        "end_line": scored_symbol["end_line"],
        "score": scored_symbol["score"],
    }
    if scored_symbol.get("container"):
        public["container"] = scored_symbol["container"]
    if "trace_step" in scored_symbol:
        public["trace_step"] = scored_symbol["trace_step"]
    return public


def _is_low_signal_symbol(symbol: Dict[str, Any]) -> bool:
    rel = Path(symbol["path"])
    return any(part.lower() in LOW_SIGNAL_PATH_PARTS for part in rel.parts)


def _symbol_key(symbol: Dict[str, Any]) -> tuple[str, str, int]:
    return (symbol["path"], symbol["symbol"], symbol["start_line"])


def _passes_graph_gate(scored_symbol: Dict[str, Any], query_tokens: set[str]) -> bool:
    required_coverage = max(1, _required_coverage(query_tokens) - 1)
    if scored_symbol["coverage_count"] < required_coverage:
        return False
    if scored_symbol["score"] < 9.0:
        return False
    if query_tokens & AUTH_QUERY_HINTS and scored_symbol.get("domain_hits", 0) == 0:
        return False
    if _is_low_signal_symbol(scored_symbol):
        return False
    return True


def _load_graph_candidate(
    root_path: Path,
    query: str,
    *,
    query_tokens: set[str],
    by_key: Dict[tuple[str, str, int], Dict[str, Any]],
    scored_by_key: Dict[tuple[str, str, int], Dict[str, Any]],
    key: tuple[str, str, int],
) -> Optional[Dict[str, Any]]:
    existing = scored_by_key.get(key)
    if existing is not None:
        return existing

    symbol = by_key.get(key)
    if symbol is None:
        return None

    candidate = dict(symbol)
    candidate.update(_score_symbol(root_path, query, symbol))
    if not _passes_graph_gate(candidate, query_tokens):
        return None

    scored_by_key[key] = candidate
    return candidate


def _graph_neighbors(symbol: Dict[str, Any], *, direction: str) -> List[Dict[str, Any]]:
    if direction == "backward":
        return list(symbol.get("caller_edges", []))
    if direction == "forward":
        return list(symbol.get("call_edges", []))
    return []


def _sort_ranked_symbols(symbols: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    symbols.sort(
        key=lambda item: (
            -item["score"],
            -item["coverage_count"],
            item["path"],
            item["start_line"],
            item["symbol"],
        )
    )
    return symbols


def _graph_neighbor_signal(
    query: str,
    candidate: Dict[str, Any],
    *,
    direction: str,
    hop: int,
    signal: float,
    edge_confidence: float,
) -> float:
    if direction == "backward":
        decay = 0.75 if hop == 1 else 0.48
    else:
        decay = 0.82 if hop == 1 else 0.58

    boost = signal * edge_confidence * decay
    lower = query.lower()
    if direction == "backward" and any(
        term in lower for term in {"permission", "permissions", "scope", "check", "checked", "where", "flow"}
    ):
        boost *= 1.15
    if direction == "backward" and _path_tokens(candidate["path"]) & CONTROL_FLOW_PATH_HINTS:
        boost *= 1.12
    if direction == "forward" and _path_tokens(candidate["path"]) & AUTH_PATH_HINTS:
        boost *= 1.08
    return boost


def _apply_graph_propagation(
    root_path: Path,
    query: str,
    *,
    symbols: List[Dict[str, Any]],
    ranked: List[Dict[str, Any]],
    query_tokens: set[str],
    seeds: Sequence[Dict[str, Any]],
    direction: str,
) -> List[Dict[str, Any]]:
    if not ranked or not seeds:
        return ranked

    by_key = {
        _symbol_key(symbol): symbol
        for symbol in symbols
        if symbol["kind"] in {"method", "function"}
    }
    scored_by_key = {_symbol_key(item): dict(item) for item in ranked}
    boosts: Dict[tuple[str, str, int], float] = {}

    for seed_rank, seed in enumerate(seeds, start=1):
        seed_key = _symbol_key(seed)
        if seed_key not in by_key:
            continue

        frontier: List[tuple[tuple[str, str, int], float, int]] = [
            (seed_key, seed["score"] * max(0.7, 1.0 - ((seed_rank - 1) * 0.15)), 0)
        ]
        seen_states: set[tuple[tuple[str, str, int], int]] = {(seed_key, 0)}

        while frontier:
            node_key, signal, depth = frontier.pop(0)
            if depth >= 2:
                continue

            node = by_key.get(node_key)
            if node is None:
                continue

            for edge in _graph_neighbors(node, direction=direction):
                neighbor_key = edge["key"]
                if neighbor_key == seed_key:
                    continue
                candidate = _load_graph_candidate(
                    root_path,
                    query,
                    query_tokens=query_tokens,
                    by_key=by_key,
                    scored_by_key=scored_by_key,
                    key=neighbor_key,
                )
                if candidate is None:
                    continue

                hop = depth + 1
                next_signal = _graph_neighbor_signal(
                    query,
                    candidate,
                    direction=direction,
                    hop=hop,
                    signal=signal,
                    edge_confidence=float(edge.get("confidence", 0.0)),
                )
                if next_signal < 4.0:
                    continue

                max_boost = seed["score"] * (0.55 if hop == 1 else 0.32)
                boost = round(min(next_signal, max_boost), 2)
                if boost <= boosts.get(neighbor_key, 0.0):
                    continue

                boosts[neighbor_key] = boost
                candidate["graph_seed"] = seed["symbol"]
                candidate["graph_depth"] = hop
                candidate["graph_direction"] = direction

                state = (neighbor_key, hop)
                if hop < 2 and state not in seen_states:
                    frontier.append((neighbor_key, next_signal, hop))
                    seen_states.add(state)

    if not boosts:
        return ranked

    merged: List[Dict[str, Any]] = []
    for key, candidate in scored_by_key.items():
        updated = dict(candidate)
        boost = boosts.get(key)
        if boost:
            updated["graph_boost"] = boost
            updated["score"] = round(updated["score"] + boost, 2)
        merged.append(updated)

    return _sort_ranked_symbols(merged)


def _promote_callers(
    root_path: Path,
    query: str,
    *,
    symbols: List[Dict[str, Any]],
    ranked: List[Dict[str, Any]],
    query_tokens: set[str],
) -> List[Dict[str, Any]]:
    if not ranked or not _should_promote_callers(query):
        return ranked
    seeds = ranked[: min(3, len(ranked))]
    reranked = _apply_graph_propagation(
        root_path,
        query,
        symbols=symbols,
        ranked=ranked,
        query_tokens=query_tokens,
        seeds=seeds,
        direction="backward",
    )
    best_caller: Optional[Dict[str, Any]] = None
    for item in reranked:
        priority = _usage_caller_priority(item)
        if priority == (0, 0):
            continue
        if best_caller is None:
            best_caller = item
            continue
        if priority > _usage_caller_priority(best_caller):
            best_caller = item
            continue
        if priority == _usage_caller_priority(best_caller) and item["score"] > best_caller["score"]:
            best_caller = item
    if best_caller is not None:
        best_key = _symbol_key(best_caller)
        reordered = [best_caller]
        reordered.extend(item for item in reranked if _symbol_key(item) != best_key)
        return reordered
    return reranked


def _usage_caller_priority(symbol: Dict[str, Any]) -> tuple[int, int]:
    if symbol.get("graph_direction") != "backward":
        return (0, 0)

    priority = 0
    path_tokens = _path_tokens(symbol["path"])
    framework_roles = set(symbol.get("framework_roles", []))
    if "fastapi_route" in framework_roles:
        priority += 4
    if path_tokens & CONTROL_FLOW_PATH_HINTS:
        priority += 3
    if not symbol.get("caller_edges"):
        priority += 2
    if symbol.get("graph_depth") == 1:
        priority += 1
    return (priority, symbol.get("graph_depth", 0))


def _rerank_trace_step(
    root_path: Path,
    query: str,
    previous: Dict[str, Any],
    ranked: List[Dict[str, Any]],
    *,
    symbols: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not ranked:
        return ranked

    query_tokens = set(_tokenize_text(query))
    reranked = _apply_graph_propagation(
        root_path,
        query,
        symbols=symbols,
        ranked=ranked,
        query_tokens=query_tokens,
        seeds=[previous],
        direction="forward",
    )
    adjusted: List[Dict[str, Any]] = []
    previous_call_keys = {edge["key"] for edge in previous.get("call_edges", [])}
    previous_caller_keys = {edge["key"] for edge in previous.get("caller_edges", [])}
    for symbol in reranked:
        candidate = dict(symbol)
        key = _symbol_key(candidate)
        if key in previous_call_keys:
            candidate["score"] = round(candidate["score"] + 10.0, 2)
            candidate["trace_anchor"] = previous["symbol"]
        elif key in previous_caller_keys:
            candidate["score"] = round(candidate["score"] + 3.0, 2)
            candidate["trace_anchor"] = previous["symbol"]
        adjusted.append(candidate)
    return _sort_ranked_symbols(adjusted)


def _search_symbols_with_symbols(
    root_path: Path,
    query: str,
    *,
    symbols: List[Dict[str, Any]],
    max_symbols: int,
    trace_step: Optional[int] = None,
) -> List[Dict[str, Any]]:
    query_tokens = set(_tokenize_text(query))
    ranked: List[Dict[str, Any]] = []
    for symbol in symbols:
        metrics = _score_symbol(root_path, query, symbol)
        scored = dict(symbol)
        scored.update(metrics)
        ranked.append(scored)

    ranked = [item for item in ranked if _passes_confidence(item, query_tokens)]
    if any(item["kind"] in {"method", "function"} for item in ranked):
        ranked = [item for item in ranked if item["kind"] in {"method", "function"}]
    if any(not _is_low_signal_symbol(item) for item in ranked):
        ranked = [item for item in ranked if not _is_low_signal_symbol(item)]
    ranked = _sort_ranked_symbols(ranked)
    ranked = _promote_callers(root_path, query, symbols=symbols, ranked=ranked, query_tokens=query_tokens)
    if trace_step is not None:
        for item in ranked:
            item["trace_step"] = trace_step
    return ranked[:max_symbols]


def search_symbols(
    root: str | Path,
    query: str,
    *,
    max_symbols: int = 10,
    ignore: Optional[Iterable[str]] = None,
) -> List[Dict[str, Any]]:
    root_path = Path(root).resolve()
    symbols = _collect_symbols(root_path, ignore or ())
    steps = _query_steps(query)
    if len(steps) == 1:
        ranked = _search_symbols_with_symbols(root_path, query, symbols=symbols, max_symbols=max_symbols)
        return [_public_symbol(item) for item in ranked]

    results: List[Dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()
    step_rankings: List[List[Dict[str, Any]]] = []
    for step_index, step in enumerate(steps, start=1):
        ranked = _search_symbols_with_symbols(
            root_path,
            step,
            symbols=symbols,
            max_symbols=max_symbols,
            trace_step=step_index,
        )
        step_rankings.append(ranked)

    if any(not ranked for ranked in step_rankings):
        return []

    for index in range(1, len(step_rankings)):
        previous_best = step_rankings[index - 1][0]
        step_rankings[index] = _rerank_trace_step(
            root_path,
            steps[index],
            previous_best,
            step_rankings[index],
            symbols=symbols,
        )

    # Reserve one slot per step first so chains stay legible.
    for ranked in step_rankings:
        for symbol in ranked:
            key = (symbol["path"], symbol["symbol"], symbol["start_line"])
            if key in seen:
                continue
            seen.add(key)
            results.append(dict(symbol))
            break
    results.sort(
        key=lambda item: (
            item.get("trace_step", 0),
            -item["score"],
            -item["coverage_count"],
            item["path"],
            item["start_line"],
            item["symbol"],
        )
    )
    return [_public_symbol(item) for item in results[:max_symbols]]


def _find_supporting_symbol(symbols: List[Dict[str, Any]], current: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    container = current.get("container")
    if not container:
        return None
    for symbol in symbols:
        if symbol["path"] != current["path"]:
            continue
        if symbol["name"] == container and symbol["kind"] in {"class", "impl"}:
            return symbol
    return None


def get_context_read_plan(
    root: str | Path,
    query: str,
    *,
    max_tokens: int = 800,
    max_symbols: int = 5,
    max_lines: int = 120,
    ignore: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    root_path = Path(root).resolve()
    symbols = _collect_symbols(root_path, ignore or ())
    steps = _query_steps(query)
    if len(steps) == 1:
        ranked = _search_symbols_with_symbols(root_path, query, symbols=symbols, max_symbols=max_symbols)
        top_symbols = [_public_symbol(item) for item in ranked]
    else:
        top_symbols = search_symbols(root_path, query, max_symbols=max_symbols, ignore=ignore)

    entries: List[Dict[str, Any]] = []
    for symbol in top_symbols:
        entry = dict(symbol)
        support = _find_supporting_symbol(symbols, symbol)
        if support:
            entry["supporting_symbol"] = {
                "symbol": support["symbol"],
                "path": support["path"],
                "start_line": support["start_line"],
                "end_line": support["end_line"],
                "kind": support["kind"],
            }
        entries.append(entry)

    return {
        "query": query,
        "max_tokens": max_tokens,
        "max_symbols": max_symbols,
        "max_lines": max_lines,
        "entries": entries,
    }


def _render_section(root: Path, symbol: Dict[str, Any], *, title: str) -> Dict[str, Any]:
    path = root / symbol["path"]
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    start = max(1, symbol["start_line"])
    end = min(len(lines), symbol["end_line"])
    language = _language_for_suffix(path.suffix.lower())
    body = "\n".join(lines[start - 1 : end])
    content = (
        f"### {title}: {symbol['symbol']}\n"
        f"{symbol['path']}:{start}-{end}\n"
        f"```{language}\n"
        f"{body}\n"
        f"```"
    )
    return {
        "title": title,
        "symbol": symbol["symbol"],
        "path": symbol["path"],
        "start_line": start,
        "end_line": end,
        "kind": symbol["kind"],
        "content": content,
    }


def materialize_context(
    root: str | Path,
    plan: Dict[str, Any],
    *,
    max_tokens: Optional[int] = None,
    max_symbols: Optional[int] = None,
    max_lines: Optional[int] = None,
) -> Dict[str, Any]:
    root_path = Path(root).resolve()
    budget_tokens = max_tokens if max_tokens is not None else int(plan.get("max_tokens", 800))
    budget_symbols = max_symbols if max_symbols is not None else int(plan.get("max_symbols", 5))
    budget_lines = max_lines if max_lines is not None else int(plan.get("max_lines", 120))

    rendered_sections: List[Dict[str, Any]] = []
    combined_parts: List[str] = []
    token_count = 0
    line_count = 0
    truncated = False

    for entry in plan.get("entries", [])[:budget_symbols]:
        sections_to_add: List[Dict[str, Any]] = []
        support = entry.get("supporting_symbol")
        if support:
            sections_to_add.append(_render_section(root_path, support, title="Context"))
        sections_to_add.append(_render_section(root_path, entry, title="Primary"))

        for section in sections_to_add:
            section_tokens = _approx_token_count(section["content"])
            section_lines = len(section["content"].splitlines())
            if token_count + section_tokens > budget_tokens or line_count + section_lines > budget_lines:
                truncated = True
                continue
            section["token_count"] = section_tokens
            section["line_count"] = section_lines
            rendered_sections.append(section)
            combined_parts.append(section["content"])
            token_count += section_tokens
            line_count += section_lines

    return {
        "query": plan.get("query", ""),
        "token_count": token_count,
        "line_count": line_count,
        "truncated": truncated,
        "content": "\n\n".join(combined_parts),
        "sections": rendered_sections,
    }
