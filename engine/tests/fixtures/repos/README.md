# Retrieval Fixture Repos

These repos are static validation targets for DeCodifier retrieval work.

- `harbor_api`: focused Python service with realistic auth, permissions, and session flows.
- `atlas_workspace`: noisy multi-language monorepo with TypeScript, Java, Python, and Rust.

Both repos contain:

- real method-level auth/session logic
- caller sites for permission and token-validation questions
- non-executable naming noise
- suppressed `tests/`, `benchmarks/`, and `generated/` trees

Ground-truth expectations for the standard retrieval prompts live in
`fixtures_manifest.json`.
