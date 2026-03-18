# Contributing to DeCodifier

Thanks for helping build DeCodifier. This project is early-stage; feedback and PRs
are welcome.

## DeCodifier Core Principles

1. Local-first - user code stays on disk.
2. Model-agnostic - no vendor lock-in; any tool-capable LLM works.
3. Deterministic tools - consistent return structures for LLM parsing.
4. Human override is sacred - never apply patches silently.
5. Scratch-first development - AI writes to `scratch/` unless instructed.
6. Framework-neutral - adapters, not biases (FastAPI, Flask, Next.js, etc).
7. Compiler optional - the engine must function even without it.

## Release Branching Strategy

- main: stable alpha snapshots
- dev: active iteration
- feature/*: experimental branches
- tags: v0.1.0, v0.2.0, ...
