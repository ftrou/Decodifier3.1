from __future__ import annotations

import json
import warnings
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional, Sequence

from . import retrieval

DEFAULT_FIXTURE_REPOS_ROOT = Path(__file__).resolve().parent.parent / "engine" / "tests" / "fixtures" / "repos"
DEFAULT_BENCHMARK_SNAPSHOT_PATH = (
    Path(__file__).resolve().parent.parent / "engine" / "tests" / "fixtures" / "retrieval_fixture_benchmark.json"
)
DEFAULT_BENCHMARK_MARKDOWN_PATH = (
    Path(__file__).resolve().parent.parent / "engine" / "tests" / "fixtures" / "retrieval_fixture_benchmark.md"
)
DEFAULT_ENGINES = ("decodifier", "lexical_baseline", "embedding_baseline")
DEFAULT_TOKEN_BUDGETS = (2000, 1000, 500)
QUERY_LABELS = {
    "where is token validation enforced": "token validation",
    "where are permissions checked": "permission check",
    "where is session expiration handled": "session expiration",
    "where is refresh token generated": "refresh token",
    "trace login -> token validation": "login trace",
    "where is oauth callback state validated": "noise decoys",
}
ENGINE_LABELS = {
    "decodifier": "DeCodifier",
    "lexical_baseline": "Lexical Baseline",
    "embedding_baseline": "Embedding Baseline",
}


def load_fixture_manifest(fixtures_root: str | Path = DEFAULT_FIXTURE_REPOS_ROOT) -> Dict[str, Any]:
    root = Path(fixtures_root).resolve()
    return json.loads((root / "fixtures_manifest.json").read_text(encoding="utf-8"))


def _ratio(numerator: int, denominator: int) -> Optional[float]:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def _mean(values: Sequence[int]) -> Optional[float]:
    if not values:
        return None
    return round(mean(values), 2)


def _query_type(repo_spec: Dict[str, Any], query: str) -> str:
    return repo_spec.get("query_types", {}).get(query, "definition")


def _first_correct_hit(actual_symbols: Sequence[str], expected_symbols: Sequence[str]) -> Optional[int]:
    expected_set = set(expected_symbols)
    for index, symbol in enumerate(actual_symbols, start=1):
        if symbol in expected_set:
            return index
    return None


def _baseline_search_symbols(root: Path, query: str, *, max_symbols: int) -> List[Dict[str, Any]]:
    root_path = Path(root).resolve()
    query_tokens = set(retrieval._tokenize_text(query))
    if not query_tokens:
        return []

    ranked: List[Dict[str, Any]] = []
    for symbol in retrieval._collect_symbols(root_path, ()):
        name_tokens = set(retrieval._tokenize_text(symbol["symbol"]))
        path_tokens = retrieval._path_tokens(symbol["path"])
        snippet_tokens = set(retrieval._snippet_tokens(root_path, symbol))
        combined_tokens = name_tokens | path_tokens | snippet_tokens

        coverage_count = len(query_tokens & combined_tokens)
        if coverage_count == 0:
            continue

        name_hits = len(query_tokens & name_tokens)
        path_hits = len(query_tokens & path_tokens)
        snippet_hits = len(query_tokens & snippet_tokens)
        score = float(name_hits * 6 + path_hits * 2 + snippet_hits * 1.5 + coverage_count * 3)
        if coverage_count == len(query_tokens):
            score += 5.0
        if symbol["kind"] == "method":
            score += 2.0
        if symbol["kind"] in {"class", "impl"}:
            score -= 2.0
        if retrieval._is_low_signal_symbol(symbol):
            score -= 4.0

        scored = dict(symbol)
        scored.update(
            {
                "score": round(score, 2),
                "coverage_count": coverage_count,
            }
        )
        ranked.append(scored)

    if any(item["kind"] in {"method", "function"} for item in ranked):
        ranked = [item for item in ranked if item["kind"] in {"method", "function"}]

    ranked.sort(
        key=lambda item: (
            -item["score"],
            -item["coverage_count"],
            item["path"],
            item["start_line"],
            item["symbol"],
        )
    )
    return [retrieval._public_symbol(item) for item in ranked[:max_symbols]]


def _materialize_symbols(
    root: Path,
    query: str,
    symbols: List[Dict[str, Any]],
    *,
    max_tokens: int,
    max_symbols: int,
    max_lines: int,
) -> Dict[str, Any]:
    plan = {
        "query": query,
        "max_tokens": max_tokens,
        "max_symbols": max_symbols,
        "max_lines": max_lines,
        "entries": symbols[:max_symbols],
    }
    return retrieval.materialize_context(
        root,
        plan,
        max_tokens=max_tokens,
        max_symbols=max_symbols,
        max_lines=max_lines,
    )


def _embedding_document(root: Path, symbol: Dict[str, Any]) -> str:
    snippet = retrieval._symbol_snippet(root, symbol)
    parts = [
        symbol["symbol"],
        symbol["path"],
        symbol.get("container") or "",
        symbol["kind"],
        snippet,
    ]
    return "\n".join(part for part in parts if part)


def _normalize_dense_rows(matrix: Any) -> Any:
    import numpy as np

    if matrix.size == 0:
        return matrix
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return matrix / norms


def _build_embedding_index(root: Path) -> Dict[str, Any]:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r".*joblib will operate in serial mode.*",
            category=UserWarning,
        )
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer

    root_path = Path(root).resolve()
    symbols = retrieval._collect_symbols(root_path, ())
    documents = [_embedding_document(root_path, symbol) for symbol in symbols]
    if not documents:
        return {"symbols": [], "vectorizer": None, "reducer": None, "vectors": None}

    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        lowercase=True,
    )
    matrix = vectorizer.fit_transform(documents)
    reducer = None

    if matrix.shape[0] >= 3 and matrix.shape[1] >= 3:
        n_components = min(64, matrix.shape[0] - 1, matrix.shape[1] - 1)
        if n_components >= 2:
            reducer = TruncatedSVD(n_components=n_components, random_state=0)
            vectors = reducer.fit_transform(matrix)
        else:
            vectors = matrix.toarray()
    else:
        vectors = matrix.toarray()

    vectors = _normalize_dense_rows(vectors)
    return {
        "symbols": symbols,
        "vectorizer": vectorizer,
        "reducer": reducer,
        "vectors": vectors,
    }


def _embedding_search_symbols(
    root: Path,
    query: str,
    *,
    max_symbols: int,
    index: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    import numpy as np

    root_path = Path(root).resolve()
    embedding_index = index or _build_embedding_index(root_path)
    if not embedding_index.get("symbols") or embedding_index.get("vectorizer") is None:
        return []

    query_matrix = embedding_index["vectorizer"].transform([query])
    reducer = embedding_index.get("reducer")
    if reducer is not None:
        query_vector = reducer.transform(query_matrix)
    else:
        query_vector = query_matrix.toarray()
    query_vector = _normalize_dense_rows(query_vector)
    if query_vector.size == 0:
        return []

    scores = np.matmul(embedding_index["vectors"], query_vector[0])
    ranked: List[Dict[str, Any]] = []
    for symbol, score in zip(embedding_index["symbols"], scores):
        similarity = float(score)
        if similarity <= 0.0:
            continue
        candidate = dict(symbol)
        candidate["score"] = round(similarity, 4)
        candidate["coverage_count"] = 0
        ranked.append(candidate)

    ranked.sort(
        key=lambda item: (
            -item["score"],
            item["path"],
            item["start_line"],
            item["symbol"],
        )
    )
    return [retrieval._public_symbol(item) for item in ranked[:max_symbols]]


def _primary_sections(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [section for section in context.get("sections", []) if section.get("title") == "Primary"]


def _context_symbols(context: Dict[str, Any]) -> List[str]:
    return [section["symbol"] for section in _primary_sections(context)]


def _tokens_to_first_correct(context: Dict[str, Any], expected_symbols: Sequence[str]) -> Optional[int]:
    if not expected_symbols:
        return None

    expected_set = set(expected_symbols)
    token_total = 0
    for section in context.get("sections", []):
        token_total += int(section.get("token_count", retrieval._approx_token_count(section["content"])))
        if section.get("title") != "Primary":
            continue
        if section["symbol"] in expected_set:
            return token_total
    return None


def _status_for_case(case: Dict[str, Any]) -> str:
    if case["query_type"] == "no_answer":
        return "ignored" if case["no_answer_correct"] else "false_positive"
    if case["topk_exact"]:
        return "correct"
    if case["first_correct_hit"] is not None:
        return f"hit@{case['first_correct_hit']}"
    return "miss"


def _summarize_cases(cases: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    positive_cases = [case for case in cases if case["query_type"] != "no_answer"]
    definition_cases = [case for case in cases if case["query_type"] == "definition"]
    caller_cases = [case for case in cases if case["query_type"] == "caller"]
    trace_cases = [case for case in cases if case["query_type"] == "trace"]
    no_answer_cases = [case for case in cases if case["query_type"] == "no_answer"]
    first_hit_positions = [case["first_correct_hit"] for case in cases if case["first_correct_hit"] is not None]
    token_counts = [case["token_count"] for case in cases]
    retrieved_context_total = sum(case["retrieved_context_count"] for case in positive_cases)
    relevant_context_total = sum(case["relevant_context_count"] for case in positive_cases)
    tokens_to_first_correct = [
        case["tokens_to_first_correct"]
        for case in positive_cases
        if case["tokens_to_first_correct"] is not None
    ]

    return {
        "query_count": len(cases),
        "context_precision": (
            round(relevant_context_total / retrieved_context_total, 4)
            if retrieved_context_total
            else None
        ),
        "context_recall": _ratio(
            sum(1 for case in positive_cases if case["context_recall"]),
            len(positive_cases),
        ),
        "false_positive_rate": _ratio(sum(1 for case in cases if case["false_positive"]), len(cases)),
        "average_tokens_to_first_correct": _mean(tokens_to_first_correct),
        "top1_accuracy": _ratio(sum(1 for case in cases if case["top1_correct"]), len(cases)),
        "topk_accuracy": _ratio(sum(1 for case in cases if case["topk_exact"]), len(cases)),
        "definition_hit_rate": _ratio(
            sum(1 for case in definition_cases if case["top1_correct"]),
            len(definition_cases),
        ),
        "caller_hit_rate": _ratio(
            sum(1 for case in caller_cases if case["top1_correct"]),
            len(caller_cases),
        ),
        "trace_success_rate": _ratio(
            sum(1 for case in trace_cases if case["topk_exact"]),
            len(trace_cases),
        ),
        "no_answer_correctness": _ratio(
            sum(1 for case in no_answer_cases if case["no_answer_correct"]),
            len(no_answer_cases),
        ),
        "average_first_correct_hit": _mean([value for value in first_hit_positions if value is not None]),
        "average_context_tokens": _mean(token_counts),
    }


def _prepare_engine_query(
    engine: str,
    repo_root: Path,
    query: str,
    *,
    max_symbols: int,
    max_plan_tokens: int,
    max_lines: int,
    engine_state: Optional[Dict[str, Any]] = None,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if engine == "decodifier":
        symbols = retrieval.search_symbols(repo_root, query, max_symbols=max_symbols)
        plan = retrieval.get_context_read_plan(
            repo_root,
            query,
            max_symbols=max_symbols,
            max_tokens=max_plan_tokens,
            max_lines=max_lines,
        )
    elif engine == "lexical_baseline":
        symbols = _baseline_search_symbols(repo_root, query, max_symbols=max_symbols)
        plan = {
            "query": query,
            "max_tokens": max_plan_tokens,
            "max_symbols": max_symbols,
            "max_lines": max_lines,
            "entries": symbols[:max_symbols],
        }
    elif engine == "embedding_baseline":
        state = engine_state if engine_state is not None else {}
        repo_key = repo_root.as_posix()
        if repo_key not in state:
            state[repo_key] = _build_embedding_index(repo_root)
        symbols = _embedding_search_symbols(repo_root, query, max_symbols=max_symbols, index=state[repo_key])
        plan = {
            "query": query,
            "max_tokens": max_plan_tokens,
            "max_symbols": max_symbols,
            "max_lines": max_lines,
            "entries": symbols[:max_symbols],
        }
    else:
        raise ValueError(f"unknown benchmark engine: {engine}")
    return symbols, plan


def _run_engine_case(
    repo_root: Path,
    query: str,
    expected_symbols: Sequence[str],
    *,
    symbols: List[Dict[str, Any]],
    plan: Dict[str, Any],
    max_tokens: int,
    max_lines: int,
    max_symbols: int,
) -> Dict[str, Any]:
    context = retrieval.materialize_context(
        repo_root,
        plan,
        max_tokens=max_tokens,
        max_symbols=max_symbols,
        max_lines=max_lines,
    )

    actual_symbols = [symbol["symbol"] for symbol in symbols]
    context_symbols = _context_symbols(context)
    expected_list = list(expected_symbols)
    expected_set = set(expected_list)
    first_correct_hit = _first_correct_hit(context_symbols, expected_list) if expected_list else None
    top1_correct = context_symbols[:1] == expected_list[:1] if expected_list else context_symbols == []
    topk_exact = context_symbols[: len(expected_list)] == expected_list if expected_list else context_symbols == []
    no_answer_correct = expected_list == [] and context_symbols == []
    relevant_context_count = sum(1 for symbol in context_symbols if symbol in expected_set)
    retrieved_context_count = len(context_symbols)

    return {
        "query": query,
        "expected_symbols": expected_list,
        "actual_symbols": actual_symbols,
        "context_symbols": context_symbols,
        "top1_correct": top1_correct,
        "topk_exact": topk_exact,
        "first_correct_hit": first_correct_hit,
        "no_answer_correct": no_answer_correct,
        "context_recall": bool(expected_list) and expected_list[0] in context_symbols,
        "relevant_context_count": relevant_context_count,
        "retrieved_context_count": retrieved_context_count,
        "context_precision": (
            round(relevant_context_count / retrieved_context_count, 4)
            if expected_list and retrieved_context_count
            else None
        ),
        "tokens_to_first_correct": _tokens_to_first_correct(context, expected_list),
        "false_positive": retrieved_context_count > 0 and relevant_context_count == 0,
        "token_count": context["token_count"],
        "line_count": context["line_count"],
        "truncated": context["truncated"],
        "plan_symbols": [entry["symbol"] for entry in plan.get("entries", [])],
    }


def run_fixture_benchmark(
    *,
    fixtures_root: str | Path = DEFAULT_FIXTURE_REPOS_ROOT,
    engines: Iterable[str] = DEFAULT_ENGINES,
    token_budgets: Iterable[int] = DEFAULT_TOKEN_BUDGETS,
    max_symbols: int = 3,
    max_tokens: Optional[int] = None,
    max_lines: int = 80,
) -> Dict[str, Any]:
    root = Path(fixtures_root).resolve()
    manifest = load_fixture_manifest(root)
    engine_names = list(engines)
    budgets = [int(max_tokens)] if max_tokens is not None else [int(budget) for budget in token_budgets]
    if not budgets:
        raise ValueError("token_budgets must contain at least one budget")
    repo_order = [repo["name"] for repo in manifest["repos"]]
    query_order = list(manifest["repos"][0]["queries"].keys()) if manifest["repos"] else []

    results: Dict[str, Any] = {
        "config": {
            "fixtures_root": root.as_posix(),
            "engines": engine_names,
            "token_budgets": budgets,
            "max_symbols": max_symbols,
            "max_lines": max_lines,
        },
        "repo_order": repo_order,
        "query_order": query_order,
        "engines": {},
    }

    for engine in engine_names:
        budget_results: Dict[str, Any] = {}
        prepared_queries: Dict[tuple[str, str], tuple[List[Dict[str, Any]], Dict[str, Any]]] = {}
        engine_state: Dict[str, Any] = {}
        for repo_spec in manifest["repos"]:
            repo_root = (root / repo_spec["path"]).resolve()
            for query in repo_spec["queries"]:
                prepared_queries[(repo_spec["name"], query)] = _prepare_engine_query(
                    engine,
                    repo_root,
                    query,
                    max_symbols=max_symbols,
                    max_plan_tokens=max(budgets),
                    max_lines=max_lines,
                    engine_state=engine_state,
                )

        for budget in budgets:
            engine_cases: List[Dict[str, Any]] = []
            by_repo: Dict[str, Any] = {}
            for repo_spec in manifest["repos"]:
                repo_root = (root / repo_spec["path"]).resolve()
                repo_cases: List[Dict[str, Any]] = []
                for query, expected_symbols in repo_spec["queries"].items():
                    symbols, plan = prepared_queries[(repo_spec["name"], query)]
                    case = _run_engine_case(
                        repo_root,
                        query,
                        expected_symbols,
                        symbols=symbols,
                        plan=plan,
                        max_symbols=max_symbols,
                        max_tokens=budget,
                        max_lines=max_lines,
                    )
                    case["repo"] = repo_spec["name"]
                    case["query_type"] = _query_type(repo_spec, query)
                    case["status"] = _status_for_case(case)
                    repo_cases.append(case)
                    engine_cases.append(case)
                by_repo[repo_spec["name"]] = {
                    "summary": _summarize_cases(repo_cases),
                    "cases": repo_cases,
                }

            budget_results[str(budget)] = {
                "summary": _summarize_cases(engine_cases),
                "by_repo": by_repo,
            }

        results["engines"][engine] = {"budgets": budget_results}

    return results


def render_fixture_benchmark_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Retrieval Fixture Benchmark",
        "",
        "## Aggregate",
        "",
        "| Engine | Budget | Queries | Precision | Recall | False positives | Tokens to first correct | Top-1 | Top-K | Caller | Trace | No-answer | Avg context tokens |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for engine_name in report["config"]["engines"]:
        for budget in report["config"]["token_budgets"]:
            summary = report["engines"][engine_name]["budgets"][str(budget)]["summary"]
            lines.append(
                "| {engine} | {budget} | {query_count} | {precision} | {recall} | {false_positive} | {first_correct_tokens} | {top1} | {topk} | {caller} | {trace} | {no_answer} | {tokens} |".format(
                    engine=ENGINE_LABELS.get(engine_name, engine_name),
                    budget=budget,
                    query_count=summary["query_count"],
                    precision=_format_metric(summary["context_precision"], percent=True),
                    recall=_format_metric(summary["context_recall"], percent=True),
                    false_positive=_format_metric(summary["false_positive_rate"], percent=True),
                    first_correct_tokens=_format_metric(summary["average_tokens_to_first_correct"]),
                    top1=_format_metric(summary["top1_accuracy"], percent=True),
                    topk=_format_metric(summary["topk_accuracy"], percent=True),
                    caller=_format_metric(summary["caller_hit_rate"], percent=True),
                    trace=_format_metric(summary["trace_success_rate"], percent=True),
                    no_answer=_format_metric(summary["no_answer_correctness"], percent=True),
                    tokens=_format_metric(summary["average_context_tokens"]),
                )
            )

    for engine_name in report["config"]["engines"]:
        for budget in report["config"]["token_budgets"]:
            lines.extend(
                [
                    "",
                    f"## {ENGINE_LABELS.get(engine_name, engine_name)} ({budget} tokens)",
                    "",
                    "| Query | " + " | ".join(report["repo_order"]) + " |",
                    "| --- | " + " | ".join("---" for _ in report["repo_order"]) + " |",
                ]
            )
            case_map = {
                (repo_name, case["query"]): case
                for repo_name, repo_data in report["engines"][engine_name]["budgets"][str(budget)]["by_repo"].items()
                for case in repo_data["cases"]
            }
            for query in report["query_order"]:
                row = [QUERY_LABELS.get(query, query)]
                for repo_name in report["repo_order"]:
                    row.append(case_map[(repo_name, query)]["status"])
                lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines).strip() + "\n"


def _format_metric(value: Optional[float], *, percent: bool = False) -> str:
    if value is None:
        return "-"
    if percent:
        return f"{value * 100:.0f}%"
    if value.is_integer():
        return str(int(value))
    return f"{value:.2f}"


def write_fixture_benchmark_outputs(
    result: Dict[str, Any],
    *,
    snapshot_path: str | Path = DEFAULT_BENCHMARK_SNAPSHOT_PATH,
    markdown_path: str | Path = DEFAULT_BENCHMARK_MARKDOWN_PATH,
) -> None:
    snapshot_target = Path(snapshot_path)
    markdown_target = Path(markdown_path)
    snapshot_target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_target.write_text(render_fixture_benchmark_markdown(result), encoding="utf-8")
