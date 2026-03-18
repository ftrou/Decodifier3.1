# DeCodifier v3.1 - Developer Preview (Alpha)

DeCodifier gets code agents to the right method, caller, and framework entrypoint first.

DeCodifier is a local AI coding engine with deterministic method-first retrieval that lets LLMs
safely inspect and modify real projects. It provides the file operations, project registry, and
tool-calling plumbing an LLM needs to write shippable code without sending your repo to a cloud.

- Local-first, runs on your machine
- Model-agnostic: works with GPT / Claude / other tool-capable LLMs
- Deterministic tools: consistent return structures for reliable parsing

## Method Retrieval

DeCodifier now exposes a deterministic retrieval layer for agent-friendly code lookup:

- `search_symbols(query)` for ranked method/class hits
- `get_context_read_plan(query)` for bounded read planning
- `materialize_context(plan)` for budgeted context rendering

Current three-repo benchmark snapshot:

| System | Context Precision | Recall | False Positives |
| --- | ---: | ---: | ---: |
| DeCodifier | 58% | 100% | 0% |
| Embedding baseline | 36% | 69% | 28% |
| Lexical baseline | 28% | 62% | 44% |

On the current three-repo benchmark suite, DeCodifier outperforms lexical and embedding baselines
on precision, recall, caller/trace handling, and false-positive control.

You can also test retrieval locally from the CLI:

```bash
decodifier query "where is token validation enforced" --path /path/to/repo
```

And benchmark the static fixture repos with DeCodifier plus the lexical and embedding baselines across the default `2000`, `1000`, and `500` token budgets:

```bash
decodifier benchmark
```

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .[dev]
uvicorn engine.app.main:app --reload
```

DeCodifier stores project registry & conversations in `~/.decodifier`.
To override:

```bash
export DECODIFIER_DATA_DIR=/your/path
```

## Core Capabilities

- Deterministic method/class retrieval
- Bounded context planning and materialization
- List projects / select target
- Read files
- Save/patch files
- Create and scaffold new modules
- Build features end-to-end
- Diff-level patching (WIP)

## Tool Interface (LLM-Friendly)

```python
from decodifier.client import DeCodifierClient, handle_decodifier_tool_call
from decodifier.tool_registry import DECODIFIER_TOOLS

client = DeCodifierClient(base_url="http://127.0.0.1:8000")

result = handle_decodifier_tool_call(client, "decodifier_read_file", {
    "project_id": "core_backend",
    "path": "engine/app/main.py",
})

print(result)
```

Available tools are listed in `decodifier/tool_registry.py` and documented in `docs/tool_reference.md`.

## Architecture

LLM <-> DeCodifier tools <-> FastAPI backend <-> Project on disk

Local-only unless configured otherwise. No repo uploads. No vendor lock-in.

## Status

DeCodifier is not a production SaaS. It is ready for:

- Solo devs
- AI developers
- Early-stage builders
- Local R&D
- Notebook + VSCode workflows
- Agentic system research

Not yet ready for:

- Multi-tenant cloud deployments
- Enterprise access controls
- Repo-scale concurrency
- Untrusted user input

## Contributing

This is the alpha. Expect rough edges.
Open issues, PRs, crashes, and questions welcome.


