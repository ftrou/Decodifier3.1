from __future__ import annotations

import json
from pathlib import Path
from io import StringIO

import pytest

from decodifier.benchmark import render_fixture_benchmark_markdown, run_fixture_benchmark
from decodifier.cli import main as cli_main
from decodifier.retrieval import get_context_read_plan, materialize_context, search_symbols
from decodifier.tool_server import run_stdio_tool_server
from engine.app.main import app
from engine.app.schemas import ContextReadPlanRequest, MaterializeContextRequest, Project, SymbolSearchRequest

FIXTURE_REPOS_ROOT = Path(__file__).resolve().parent / "fixtures" / "repos"
FIXTURE_REPOS_MANIFEST = json.loads((FIXTURE_REPOS_ROOT / "fixtures_manifest.json").read_text(encoding="utf-8"))
FIXTURE_REPO_SPECS_BY_NAME = {repo["name"]: repo for repo in FIXTURE_REPOS_MANIFEST["repos"]}


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_benchmark_repo(root: Path) -> Path:
    _write(
        root / "src/auth/controller.py",
        """class AuthController:
    def login(self, username: str, password: str) -> str:
        service = AuthService()
        checker = PermissionChecker()
        session = create_session(username)
        token = service.generate_refresh_token(session)
        if not checker.check_permissions("admin"):
            raise PermissionError("forbidden")
        return service.validate_token(token)

    def get_current_user(self, token: str) -> str:
        service = AuthService()
        return service.validate_token(token)
""",
    )
    _write(
        root / "src/auth/service.py",
        """class AuthService:
    def login(self, username: str, password: str) -> str:
        session = create_session(username)
        token = self.generate_refresh_token(session)
        return self.validate_token(token)

    def validate_token(self, token: str) -> str:
        if token is None or token.startswith("expired::"):
            raise ValueError("token validation failed")
        return token

    def enforce_token_validation(self, token: str) -> str:
        return self.validate_token(token)

    def generate_refresh_token(self, session: object) -> str:
        return f"refresh::{session}"
""",
    )
    _write(
        root / "src/security/permission_checker.rs",
        """pub struct PermissionChecker {}

impl PermissionChecker {
    pub fn check_permissions(&self, scope: &str) -> bool {
        self.has_scope(scope)
    }

    fn has_scope(&self, scope: &str) -> bool {
        scope == "admin"
    }
}
""",
    )
    _write(
        root / "src/session/SessionManager.java",
        """public class SessionManager {
    public boolean handleSessionExpiration(Session session) {
        return session.expiresAt() <= clock.now();
    }
}
""",
    )
    _write(
        root / "web/auth/session.ts",
        """export class WebSessionService {
  validateBrowserToken(token: string): boolean {
    return token.startsWith("browser::");
  }

  buildRefreshSummary(token: string): string {
    return `summary:${token}`;
  }
}
""",
    )
    _write(
        root / "generated/auth/session_token.py",
        """class SessionToken:
    def validate_token_record(self, token: str) -> bool:
        return token.startswith("generated::")
""",
    )
    _write(
        root / "tests/test_auth_flow.py",
        """class AuthService:
    def validate_token(self, token: str) -> bool:
        return token.startswith("test::")
""",
    )
    _write(
        root / "benchmarks/auth_context_benchmark.py",
        """class AuthBenchmark:
    def login(self, token: str) -> bool:
        return token.startswith("bench::")
""",
    )

    for index in range(60):
        _write(
            root / f"noise/python/token_validation_banner_{index:03d}.py",
            f"""def render_token_validation_banner_{index}() -> str:
    return "token validation banner {index}"
""",
        )
        _write(
            root / f"noise/ts/session_expiration_notice_{index:03d}.ts",
            f"""export function buildSessionExpirationNotice{index}(): string {{
  return "session expiration notice {index}";
}}
""",
        )
        _write(
            root / f"noise/java/refresh_token_summary_{index:03d}.java",
            f"""public class RefreshTokenSummary{index} {{
    public String buildRefreshTokenSummary() {{
        return "refresh summary {index}";
    }}
}}
""",
        )
        _write(
            root / f"noise/rust/permission_scope_label_{index:03d}.rs",
            f"""pub fn permission_scope_label_{index}() -> &'static str {{
    "permission scope label {index}"
}}
""",
        )

    return root


def _build_surface_repo(root: Path) -> Path:
    _write(
        root / "user/calc.py",
        """def perform_calc_operation(lhs: int, rhs: int) -> int:
    return lhs + rhs


def calc_main() -> int:
    current = 0
    while True:
        line = sys_readline()
        if line == "exit":
            return current
        current = perform_calc_operation(current, 1)
""",
    )
    _write(
        root / "host/bridge.py",
        """def run_simulated_calc_line(expr: str) -> str:
    return expr


def dispatch_command(command: str, expr: str) -> str:
    if command == "calc":
        return run_simulated_calc_line(expr)
    return "unknown"
""",
    )
    return root


@pytest.fixture()
def benchmark_repo(tmp_path: Path) -> Path:
    return _build_benchmark_repo(tmp_path / "benchmark-repo")


def test_benchmark_repo_is_large_and_multilanguage(benchmark_repo: Path) -> None:
    files = [path for path in benchmark_repo.rglob("*") if path.is_file()]
    suffixes = {path.suffix for path in files}

    assert len(files) >= 200
    assert {".py", ".ts", ".java", ".rs"} <= suffixes


@pytest.mark.parametrize(
    ("query", "expected_symbol"),
    [
        ("where is token validation enforced", "AuthService.enforce_token_validation"),
        ("where are permissions checked", "AuthController.login"),
        ("where is session expiration handled", "SessionManager.handleSessionExpiration"),
        ("where is refresh token generated", "AuthService.generate_refresh_token"),
    ],
)
def test_search_symbols_returns_expected_primary_hits(
    benchmark_repo: Path,
    query: str,
    expected_symbol: str,
) -> None:
    symbols = search_symbols(benchmark_repo, query, max_symbols=5)

    assert symbols
    assert symbols[0]["symbol"] == expected_symbol


def test_trace_query_returns_login_then_validation(benchmark_repo: Path) -> None:
    symbols = search_symbols(benchmark_repo, "trace login -> token validation", max_symbols=4)

    assert [symbol["symbol"] for symbol in symbols[:2]] == [
        "AuthController.login",
        "AuthService.validate_token",
    ]


def test_trace_query_uses_resolved_call_edges_for_duplicate_method_names(tmp_path: Path) -> None:
    repo = tmp_path / "resolved-graph-repo"
    _write(
        repo / "alpha_payments/security.py",
        """class PaymentTokenService:
    def validate_token(self, token: str) -> str:
        return token
""",
    )
    _write(
        repo / "alpha_payments/routes.py",
        """class PaymentController:
    def charge(self, token: str) -> str:
        service = PaymentTokenService()
        return service.validate_token(token)
""",
    )
    _write(
        repo / "zeta_auth/security.py",
        """class AuthTokenService:
    def validate_token(self, token: str) -> str:
        return token
""",
    )
    _write(
        repo / "zeta_auth/routes.py",
        """class AuthController:
    def login_user(self, token: str) -> str:
        service = AuthTokenService()
        return service.validate_token(token)
""",
    )

    symbols = search_symbols(repo, "trace login -> token validation", max_symbols=4)

    assert [symbol["symbol"] for symbol in symbols[:2]] == [
        "AuthController.login_user",
        "AuthTokenService.validate_token",
    ]


def test_fastapi_entrypoint_anchoring_prefers_routes_and_dependencies(tmp_path: Path) -> None:
    repo = tmp_path / "fastapi-anchor-repo"
    _write(
        repo / "app/core/security.py",
        """def validate_token(token: str) -> str:
    return token
""",
    )
    _write(
        repo / "app/api/deps.py",
        """from typing import Annotated

from fastapi import Depends, HTTPException

from app.core.security import validate_token


def get_current_user(token: str) -> str:
    user = validate_token(token)
    if not user:
        raise HTTPException(status_code=403, detail="Could not validate credentials")
    return user


CurrentUser = Annotated[str, Depends(get_current_user)]
""",
    )
    _write(
        repo / "app/api/routes/items.py",
        """from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser

router = APIRouter()


@router.get("/items/{id}")
def read_item(current_user: CurrentUser, id: str) -> str:
    if current_user != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return id
""",
    )

    token_symbols = search_symbols(repo, "where is token validation enforced", max_symbols=3)
    permission_symbols = search_symbols(repo, "where are permissions checked", max_symbols=3)

    assert token_symbols[0]["symbol"] == "get_current_user"
    assert permission_symbols[0]["symbol"] == "read_item"


def test_context_read_plan_includes_supporting_class(benchmark_repo: Path) -> None:
    plan = get_context_read_plan(
        benchmark_repo,
        "where is token validation enforced",
        max_symbols=3,
        max_tokens=800,
        max_lines=80,
    )

    assert plan["entries"][0]["symbol"] == "AuthService.enforce_token_validation"
    assert plan["entries"][0]["supporting_symbol"]["symbol"] == "AuthService"


def test_search_symbols_suppresses_tests_and_benchmarks(benchmark_repo: Path) -> None:
    symbols = search_symbols(benchmark_repo, "where is token validation enforced", max_symbols=5)

    assert symbols
    assert all(not symbol["path"].startswith("tests/") for symbol in symbols)
    assert all(not symbol["path"].startswith("benchmarks/") for symbol in symbols)


def test_search_symbols_prefers_real_code_over_generated_matches(benchmark_repo: Path) -> None:
    symbols = search_symbols(benchmark_repo, "where is token validation enforced", max_symbols=3)

    assert symbols[0]["path"] == "src/auth/service.py"
    assert all(not symbol["path"].startswith("generated/") for symbol in symbols)


def test_search_symbols_promotes_permission_call_site(benchmark_repo: Path) -> None:
    symbols = search_symbols(benchmark_repo, "where are permissions checked", max_symbols=3)

    assert [symbol["symbol"] for symbol in symbols[:2]] == [
        "AuthController.login",
        "PermissionChecker.check_permissions",
    ]


def test_search_symbols_include_rationale_and_surfaces(benchmark_repo: Path) -> None:
    symbols = search_symbols(benchmark_repo, "where are permissions checked", max_symbols=3)

    assert "caller" in symbols[0]["behavior_surfaces"]
    assert any(reason.startswith("matched query tokens:") for reason in symbols[0]["rationale"])
    assert symbols[0]["debug"]["matched_query_tokens"]


def test_context_read_plan_exposes_surface_bundle(benchmark_repo: Path) -> None:
    plan = get_context_read_plan(
        benchmark_repo,
        "where are permissions checked",
        max_symbols=4,
        max_tokens=800,
        max_lines=80,
    )

    bundle_surfaces = [item["surface"] for item in plan["surface_bundle"]]
    bundle_symbols = [item["symbol"] for item in plan["surface_bundle"]]

    assert "caller" in bundle_surfaces
    assert "implementation" in bundle_surfaces
    assert "AuthController.login" in bundle_symbols
    assert "PermissionChecker.check_permissions" in bundle_symbols


def test_search_symbols_returns_empty_when_repo_has_no_good_answer(benchmark_repo: Path) -> None:
    symbols = search_symbols(benchmark_repo, "where is oauth callback state validated", max_symbols=5)

    assert symbols == []


def test_search_symbols_ignores_query_expansion_helpers(tmp_path: Path) -> None:
    repo = tmp_path / "helper-repo"
    _write(
        repo / "engine/app/indexer.py",
        """def _normalized_search_text(text: str) -> str:
    text = re.sub(r"([a-z0-9])([A-Z])", r"\\1 \\2", text)
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\\1 \\2", text)
    return text.lower()


def _search_terms(query: str):
    expansions = {
        "validation": ("validate", "verify"),
        "permissions": ("permission", "scope"),
        "checked": ("check",),
    }
    return expansions.get(query, ())
""",
    )

    symbols = search_symbols(repo, "where are permissions checked", max_symbols=3)

    assert symbols == []


def test_generic_entrypoint_anchoring_groups_dispatch_and_simulation(tmp_path: Path) -> None:
    repo = _build_surface_repo(tmp_path / "surface-repo")

    symbols = search_symbols(repo, "simulate calc command", max_symbols=5)
    plan = get_context_read_plan(repo, "simulate calc command", max_symbols=5, max_tokens=800, max_lines=80)

    assert symbols[0]["symbol"] in {"dispatch_command", "run_simulated_calc_line"}
    bundle_surfaces = {item["surface"] for item in plan["surface_bundle"]}
    bundle_symbols = {item["symbol"] for item in plan["surface_bundle"]}
    assert {"dispatcher", "simulation", "entrypoint"} & bundle_surfaces
    assert "run_simulated_calc_line" in bundle_symbols
    assert {"dispatch_command", "run_simulated_calc_line", "calc_main"} & bundle_symbols


@pytest.mark.parametrize(
    ("repo_name", "query", "expected_prefix"),
    [
        (repo["name"], query, expected)
        for repo in FIXTURE_REPOS_MANIFEST["repos"]
        for query, expected in repo["queries"].items()
    ],
)
def test_fixture_repo_search_symbols_match_manifest(
    repo_name: str,
    query: str,
    expected_prefix: list[str],
) -> None:
    repo_root = (FIXTURE_REPOS_ROOT / FIXTURE_REPO_SPECS_BY_NAME[repo_name]["path"]).resolve()

    symbols = search_symbols(repo_root, query, max_symbols=max(3, len(expected_prefix)))
    if not expected_prefix:
        assert symbols == []
        return

    assert [symbol["symbol"] for symbol in symbols[: len(expected_prefix)]] == expected_prefix


@pytest.mark.parametrize(
    ("repo_name", "query", "expected_symbols"),
    [
        (repo["name"], "trace login -> token validation", repo["queries"]["trace login -> token validation"])
        for repo in FIXTURE_REPOS_MANIFEST["repos"]
    ],
)
def test_fixture_repo_context_plan_covers_trace_expectations(
    repo_name: str,
    query: str,
    expected_symbols: list[str],
) -> None:
    repo_root = (FIXTURE_REPOS_ROOT / FIXTURE_REPO_SPECS_BY_NAME[repo_name]["path"]).resolve()

    plan = get_context_read_plan(
        repo_root,
        query,
        max_symbols=3,
        max_tokens=800,
        max_lines=80,
    )
    context = materialize_context(
        repo_root,
        plan,
        max_tokens=800,
        max_symbols=3,
        max_lines=80,
    )

    assert [entry["symbol"] for entry in plan["entries"][: len(expected_symbols)]] == expected_symbols
    for symbol in expected_symbols:
        assert symbol in context["content"]
    assert context["token_count"] <= 800


@pytest.mark.parametrize("budget", [2000, 1000, 500])
def test_materialize_context_respects_budgets(benchmark_repo: Path, budget: int) -> None:
    plan = get_context_read_plan(
        benchmark_repo,
        "trace login -> token validation",
        max_symbols=3,
        max_tokens=budget,
        max_lines=80,
    )
    context = materialize_context(
        benchmark_repo,
        plan,
        max_tokens=budget,
        max_symbols=3,
        max_lines=80,
    )

    assert context["token_count"] <= budget
    assert "AuthController.login" in context["content"]
    assert "AuthService.validate_token" in context["content"]


def test_retrieval_benchmark_snapshot(benchmark_repo: Path) -> None:
    snapshot_path = Path(__file__).resolve().parent / "fixtures" / "retrieval_snapshot.json"
    expected = json.loads(snapshot_path.read_text(encoding="utf-8"))

    queries = [
        "where is token validation enforced",
        "where are permissions checked",
        "where is session expiration handled",
        "where is refresh token generated",
        "trace login -> token validation",
    ]
    budgets = [2000, 1000, 500]

    actual = {"queries": {}, "budgets": {}, "metrics": {}}
    for query in queries:
        symbols = search_symbols(benchmark_repo, query, max_symbols=3)
        actual["queries"][query] = [symbol["symbol"] for symbol in symbols]
    for budget in budgets:
        plan = get_context_read_plan(
            benchmark_repo,
            "trace login -> token validation",
            max_symbols=3,
            max_tokens=budget,
            max_lines=80,
        )
        context = materialize_context(
            benchmark_repo,
            plan,
            max_tokens=budget,
            max_symbols=3,
            max_lines=80,
        )
        actual["budgets"][str(budget)] = {
            "symbols": [entry["symbol"] for entry in plan["entries"]],
            "token_count": context["token_count"],
            "line_count": context["line_count"],
            "truncated": context["truncated"],
        }
    actual["metrics"]["usage_query_top_hit_is_caller"] = (
        actual["queries"]["where are permissions checked"][:1] == ["AuthController.login"]
    )

    assert actual == expected


def test_fixture_benchmark_snapshot() -> None:
    snapshot_path = Path(__file__).resolve().parent / "fixtures" / "retrieval_fixture_benchmark.json"
    expected = json.loads(snapshot_path.read_text(encoding="utf-8"))

    actual = run_fixture_benchmark(fixtures_root=FIXTURE_REPOS_ROOT)

    assert actual == expected


def test_fixture_benchmark_markdown_snapshot() -> None:
    snapshot_path = Path(__file__).resolve().parent / "fixtures" / "retrieval_fixture_benchmark.md"
    expected = snapshot_path.read_text(encoding="utf-8")

    actual = render_fixture_benchmark_markdown(run_fixture_benchmark(fixtures_root=FIXTURE_REPOS_ROOT))

    assert actual == expected


def test_retrieval_endpoints(monkeypatch: pytest.MonkeyPatch, benchmark_repo: Path) -> None:
    project = Project(id="bench", name="bench", path=str(benchmark_repo))

    from engine.app import main, storage

    monkeypatch.setattr(storage, "get_project", lambda project_id: project if project_id == "bench" else None)

    route_paths = {route.path for route in app.routes}
    assert "/api/search_symbols" in route_paths
    assert "/api/context_read_plan" in route_paths
    assert "/api/materialize_context" in route_paths

    search_response = main.search_symbols(
        SymbolSearchRequest(project_id="bench", query="where is refresh token generated", max_symbols=3)
    )
    assert search_response.symbols[0].symbol == "AuthService.generate_refresh_token"

    plan_response = main.context_read_plan(
        ContextReadPlanRequest(
            project_id="bench",
            query="where is token validation enforced",
            max_symbols=3,
            max_tokens=800,
            max_lines=80,
        )
    )
    assert plan_response.entries[0].symbol == "AuthService.enforce_token_validation"

    materialize_response = main.materialize_context(
        MaterializeContextRequest(
            project_id="bench",
            plan=plan_response,
            max_tokens=500,
            max_symbols=3,
            max_lines=80,
        )
    )
    assert "AuthService.enforce_token_validation" in materialize_response.content


def test_cli_query_outputs_symbol_and_path(benchmark_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli_main(
        [
            "query",
            "where is refresh token generated",
            "--path",
            str(benchmark_repo),
            "--max-symbols",
            "2",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "AuthService.generate_refresh_token" in output
    assert "src/auth/service.py" in output


def test_cli_query_debug_outputs_rationale(benchmark_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli_main(
        [
            "query",
            "where are permissions checked",
            "--path",
            str(benchmark_repo),
            "--max-symbols",
            "1",
            "--debug",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "surfaces:" in output
    assert "why: matched query tokens:" in output
    assert "debug:" in output


def test_cli_benchmark_writes_outputs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    snapshot_path = tmp_path / "benchmark.json"
    markdown_path = tmp_path / "benchmark.md"

    exit_code = cli_main(
        [
            "benchmark",
            "--fixtures-root",
            str(FIXTURE_REPOS_ROOT),
            "--snapshot-out",
            str(snapshot_path),
            "--markdown-out",
            str(markdown_path),
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert snapshot_path.exists()
    assert markdown_path.exists()
    assert "Retrieval Fixture Benchmark" in output


def test_stdio_tool_server_round_trip(benchmark_repo: Path) -> None:
    request_stream = StringIO(
        json.dumps({"id": 1, "tool": "search_symbols", "arguments": {"query": "where is refresh token generated", "max_symbols": 2}})
        + "\n"
        + json.dumps({"id": 2, "tool": "get_context_read_plan", "arguments": {"query": "where are permissions checked", "max_symbols": 3}})
        + "\n"
    )
    response_stream = StringIO()

    exit_code = run_stdio_tool_server(benchmark_repo, instream=request_stream, outstream=response_stream)
    responses = [json.loads(line) for line in response_stream.getvalue().splitlines() if line.strip()]

    assert exit_code == 0
    assert responses[0]["ok"] is True
    assert responses[0]["result"]["symbols"][0]["symbol"] == "AuthService.generate_refresh_token"
    assert responses[1]["ok"] is True
    assert responses[1]["result"]["surface_bundle"]
