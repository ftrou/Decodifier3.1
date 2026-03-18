# Decodifier  
### **The Compiler for AI-Generated Software**

**LLMs don’t write code.**  
They write **intent**.  
Decodifier compiles that intent into working software.

---

## 🚀 What is Decodifier?

Decodifier is a new layer in the AI stack:

> **A compiler for LLM-generated software.  
> LLMs write specs. Decodifier builds the code.**

Instead of prompting models to generate Python, TypeScript, or SQL directly, LLMs (or humans) produce **small declarative specs**. Decodifier validates them, compiles them, and updates the codebase — **without the model ever reading or editing files.**

This creates a **token firewall** between LLMs and codebases:

- LLMs stay at the **architecture & intent** level  
- Decodifier handles the **code**  
- Projects stay consistent, safe, and scalable

---

## 🧩 Why this matters

AI coding today is stuck in a chat window:  
LLMs regenerate files, hallucinate imports, and break architecture.

With Decodifier:

| Without Decodifier | With Decodifier |
|-------------------|-----------------|
| “Write a FastAPI endpoint for users” | ```yaml<br>kind: backend.http_endpoint<br>name: create_user<br>path: "/api/users"<br>method: post``` |
| 200–800 tokens of code | **8 lines of intent** |
| LLM must read repo | **No repo access needed** |
| Architecture drifts | Architecture is enforced |
| Code is the medium | **Specs are the medium** |

**Result:**  
LLMs develop features without touching code.

---

## 🏗️ What it looks like

**input →**

```yaml
# patterns/specs/backend.user.create.yaml
kind: backend.http_endpoint
name: create_user
path: "/api/users"
method: post
request_model: UserCreate
response_model: User

command →

curl -X POST "http://localhost:8000/patterns/build" \
  -H "Content-Type: application/json" \
  -d '{"spec_dir": "patterns/specs", "project_root": "."}'

output →

backend/api/generated_endpoints.py  ✓
backend/request_schemas.py          ✓
backend/response_schemas.py         ✓

LLM never saw or generated these files.
🎛️ Core Concepts
1. Patterns

Reusable architecture definitions.

Examples:

    backend.model

    backend.http_endpoint

    backend.crud

    backend.request_schema

    backend.storage

    agent.llm_chat

    service.queue_worker

2. Specs

Tiny YAML files produced by humans or LLMs.
3. Compiler

Validates → normalizes → generates → wires code.
4. Token Firewall

LLMs do not read or modify source files.
They operate entirely through specs + build results.
📉 Why this saves tokens

LLMs don’t waste compute on:

    repo embeddings

    code diffs

    file rewrites

    correcting hallucinated imports

Instead of generating code, they generate intent.

This reduces token usage by 60–90% in AI-assisted development.
📈 Why this matters at scale

If adopted inside a large organization:

    Fewer GPUs needed for development workflows

    Models don’t need huge context windows for legacy repos

    Smaller models can do more work

    Architecture becomes enforceable, not optional

    At hyperscaler scale, this could represent
    $100M–$500M/year in net efficiency
    (compute + engineering time), even with partial rollout.

📌 Status
Version	Stage	What it does
v0.1	PROTOTYPE	LLM-safe file read/write + project ops
v0.2	CURRENT	Pattern engine, validator, FastAPI backend generation
v0.3	In Progress	No-Code-for-LLMs: full backend extension without reading code
v1.0	ROADMAP	Pattern packs, DB/CRUD, agents, auth, diff-safe generation
🎯 v0.3 Mission

    A full backend can be extended without the LLM ever reading the generated code.

Milestones:

    backend.model generator

    backend.crud integration

    request/response schema emitters

    router auto-mount

    test harness generation

This will complete the first end-to-end pattern chain.
🛡️ License

To protect the core compiler logic and prevent closed SaaS forks:

AGPL-3.0

This license allows public use, contributions, and research —
but requires that improvements remain open if used as a hosted service.
💬 Getting Started

pip install -r requirements.txt
uvicorn engine.app.main:app --reload
open http://localhost:8000/dashboard

Add a spec → click Generate from Specs → watch the backend evolve.
📣 Join the Category

    Decodifier is the first compiler for AI-generated software.
    LLMs don’t need to write code. They need a compiler that does.

If you’re building AI systems and want to collaborate, open an issue or reach out.

This isn’t a tool.
This is a new layer.
🧠 Vision

Software creation becomes:

Architecture → Patterns → Specs → Compiler → Code → Running System

LLMs operate at the architecture tier.
Decodifier handles the rest.

This is how AI development scales.