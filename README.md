# DeCodifier v3.1 - Developer Preview (Alpha)

DeCodifier gets code agents to the full behavioral change surface first.

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
- behavior-surface bundles for entrypoints, callers, implementations, guards, dispatchers, REPLs, simulators, and bridges
- per-hit rationale/debug metadata so agents can inspect why a symbol ranked where it did

## Benchmarks

DeCodifier is built around a simple idea:

Code agents usually need the full behavioral change surface first, not just the right file.

That means retrieving the set of implementation surfaces that must stay aligned in a real change,
such as the entrypoint, the caller, the implementation, the guard, and supporting surfaces like a
bridge, simulation, or REPL path.

### Repo Set

The current benchmark suite covers three realistic repo archetypes:

- `harbor_api` - clean Python auth service
- `atlas_workspace` - noisy multi-language workspace
- `fastapi_full_stack_backend` - FastAPI backend with dependency-injection auth

### Change-Surface Headline

| System | Anchor Recall | Surface-Bundle Recall | Full Change-Set Rate | False Positives |
| --- | ---: | ---: | ---: | ---: |
| DeCodifier | 100% | 100% | 100% | 0% |
| Embedding baseline | 85% | 0% | 20% | 28% |
| Lexical baseline | 65% | 0% | 20% | 44% |

### Retrieval Quality Headline

| System | Context Precision | Recall | False Positives |
| --- | ---: | ---: | ---: |
| DeCodifier | 58% | 100% | 0% |
| Embedding baseline | 36% | 69% | 28% |
| Lexical baseline | 28% | 62% | 44% |

### Behavioral Correctness Headline

Across the current benchmark repos, DeCodifier also achieves:

- 100% top-1 correctness
- 100% top-k correctness
- 100% caller correctness
- 100% trace correctness
- 100% no-answer correctness

The lexical baseline falls to:

- 39% top-1 correctness
- 33% top-k correctness
- 0% caller correctness
- 0% trace correctness
- 0% no-answer correctness

### What These Metrics Mean

- `Anchor Recall` - whether retrieval surfaced the main behavioral anchor for the task
- `Surface-Bundle Recall` - whether retrieval returned the bundle of surfaces that should be changed together
- `Full Change-Set Rate` - whether an agent could recover the complete coordinated change surface, not just one relevant snippet
- `False Positives` - how often retrieval confidently returned junk

This matters because code agents often fail by finding one plausible file and missing the rest of
the change surface. DeCodifier is designed to return the full behavioral bundle instead.

### Why This Is Different

Traditional retrieval usually operates at the file or chunk level.

DeCodifier operates at the behavior level:

- method-first retrieval
- caller anchoring
- framework entrypoint detection
- trace query handling
- grouped surface bundles
- strict no-answer protection

That makes it better suited for questions like:

- `where is token validation enforced`
- `where are permissions checked`
- `trace login -> token validation`
- `what surfaces need to change together`

### Codex Dogfood Run: Coordinated Calculator Change on a Real Repo

A recent live Codex + MCP run used DeCodifier on a separate local OS project to expand a calculator from basic arithmetic to a broader integer-math feature set.

**What DeCodifier changed**

Without DeCodifier, this task looked like a likely single-file patch in the guest calculator source.

With DeCodifier retrieval first, Codex surfaced the actual **behavioral change surface**:

- the guest calculator implementation in `user/calc.c`
- the mirrored host-side calculator logic in `model/qwen_chat.py`
- the user-facing capability and help text that needed to stay aligned

That changed the plan from “patch the obvious file” to “patch the full surface that defines calculator behavior across guest and host paths.”

**Why this mattered**

The calculator logic existed in more than one place. Updating only the guest implementation would have created drift between:

- the real interactive calculator in the OS
- the host-side mirrored and simulated path used by the bridge

DeCodifier made Codex less likely to stop at the first plausible file and more likely to update the full behavior surface safely.

**What changed**

The final patch added a broader integer-math feature set and kept both execution paths aligned, including:

- new unary helpers
- new binary and bitwise helpers
- parser and alias updates
- help text updates
- host-side mirrored behavior updates

The bridge transport itself did not require protocol changes. The important work was keeping the behavior layers aligned above it.

**Verification**

Focused verification passed:

- `python3 -m py_compile model/qwen_chat.py`
- `make kernel.elf`
- a targeted calculator harness covering valid, chained, function-style, and invalid or overflow cases

Note: this was a focused verification pass, not a full QEMU or full OS regression run. In that environment, direct import of the host bridge module was blocked by a missing `torch` dependency, so the calculator verification used a calc-only extracted harness from the mirrored Python logic.

**Takeaway**

This is the kind of change DeCodifier is built for: not just finding a relevant file, but recovering the **full behavioral change surface** that a code agent needs to modify together.

See [docs/case_studies.md](docs/case_studies.md) for the longer case-study version.

### Token Budgets

The benchmark runs under fixed token budgets and evaluates the actual materialized context returned
to the model, not just raw search hits. Current results are stable across `2000`, `1000`, and
`500` token budgets.

The goal is not just to retrieve something relevant. The goal is to retrieve the right behavioral
surface under tight context limits.

### Current Limitations

This is still an early benchmark suite.

Current strengths:

- deterministic structural retrieval
- method / caller / entrypoint ranking
- change-surface recovery
- strict no-answer behavior

What still needs broader validation:

- more external public repos
- larger monorepos
- additional frameworks beyond the current benchmark set

### Bottom Line

DeCodifier is not just optimized to find the right method. It is optimized to recover the full
behavioral change surface a code agent must modify together.

You can also test retrieval locally from the CLI:

```bash
decodifier query "where is token validation enforced" --path /path/to/repo
```

And benchmark the static fixture repos with DeCodifier plus the lexical and embedding baselines across the default `2000`, `1000`, and `500` token budgets:

```bash
decodifier benchmark
```

The benchmark now tracks change-oriented retrieval quality as well as first-hit accuracy, including
anchor-set recall, surface-bundle recall, full change-surface success, and tokens to the full
retrieval set.

For Codex, Claude Code, and other MCP-capable agents, you can expose the retrieval tools over
stdio MCP:

```bash
decodifier mcp-server --path /path/to/repo
```

You can also print ready-to-use adapter snippets for Codex and Claude Code:

```bash
decodifier adapter codex --path /path/to/repo
decodifier adapter claude-code --path /path/to/repo
```

The adapter output includes:

- a one-line install command for the target agent
- a config snippet for `~/.codex/config.toml` or `.mcp.json`
- a short instruction block you can drop into `AGENTS.md` or `CLAUDE.md`

For legacy local integrations, the older newline-delimited JSON tool server is still available:

```bash
decodifier tool-server --path /path/to/repo
```

Send newline-delimited requests like:

```json
{"id":1,"tool":"search_symbols","arguments":{"query":"where are permissions checked","max_symbols":3}}
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
