# Architecture

LLM <-> DeCodifier tools <-> FastAPI engine <-> Project on disk

The engine exposes REST endpoints for safe reads/writes, project registry,
indexing, and audit events. Tool adapters translate LLM tool calls into these
endpoints.
