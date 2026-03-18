"""
patterns_backend_demo.py

Demo: let an LLM use Decodifier's patterns engine to build a small FastAPI backend.

Flow:

    LLM -> writes YAML specs under patterns/specs/
        -> calls /patterns/build
        -> Decodifier generates/updates backend/api/*.py
        -> (optional) LLM reads generated files for verification

Prereqs:
    - Decodifier repo checked out
    - uvicorn engine.app.main:app --reload running from repo root
    - OPENAI_API_KEY set in your environment
"""

import json
import os
from typing import Any, Dict

import requests
from openai import OpenAI

# --- CONFIG -------------------------------------------------------------------
TOTAL_INPUT_TOKENS = 0
TOTAL_OUTPUT_TOKENS = 0
CALLS = 0

DECO_ROOT = os.environ.get(
    "DECODIFIER_ROOT",
    "/mnt/c/Users/jwmar/desktop/decodifier",  # adjust if your path differs
)
ENGINE_URL = os.environ.get("DECODIFIER_ENGINE_URL", "http://127.0.0.1:8000")
OPENAI_MODEL = os.environ.get("DECODIFIER_MODEL", "gpt-4.1-mini")

# --- TOOL DEFINITIONS (sent to the LLM) ---------------------------------------

PATTERN_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "write_spec_file",
            "description": (
                "Create or overwrite a Decodifier spec file (YAML) at the given "
                "path relative to the repo root. Use this instead of editing "
                "Python files directly."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Spec path, e.g. 'patterns/specs/backend.http_endpoint.users.yaml'",
                    },
                    "content": {
                        "type": "string",
                        "description": "YAML content of the spec file.",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_patterns_build",
            "description": (
                "Run Decodifier's pattern build to apply all current specs. "
                "This compiles specs into backend code."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "spec_dir": {
                        "type": "string",
                        "description": "Directory containing spec files.",
                        "default": "patterns/specs",
                    },
                    "project_root": {
                        "type": "string",
                        "description": "Project root (usually '.').",
                        "default": ".",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read a text file from the Decodifier project so you can inspect "
                "generated code. Treat the result as read-only."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to a file under the project root.",
                    }
                },
                "required": ["path"],
            },
        },
    },
]

# --- TOOL IMPLEMENTATIONS (what actually runs) --------------------------------


def _abs_path(rel_path: str) -> str:
    return os.path.join(DECO_ROOT, rel_path)


def write_spec_file_impl(path: str, content: str) -> Dict[str, Any]:
    abs_path = _abs_path(path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(content)
    return {"status": "ok", "path": path, "bytes": len(content)}


def run_patterns_build_impl(
    spec_dir: str = "patterns/specs", project_root: str = "."
) -> Dict[str, Any]:
    payload = {"spec_dir": spec_dir, "project_root": project_root}
    resp = requests.post(f"{ENGINE_URL}/patterns/build", json=payload, timeout=90)
    resp.raise_for_status()
    # your /patterns/build already returns a summary (patterns/specs/files/errors)
    return resp.json()


def read_file_impl(path: str) -> Dict[str, Any]:
    abs_path = _abs_path(path)
    if not os.path.exists(abs_path):
        return {"exists": False, "path": path}
    with open(abs_path, "r", encoding="utf-8") as f:
        return {"exists": True, "path": path, "content": f.read()}


TOOL_IMPLS = {
    "write_spec_file": write_spec_file_impl,
    "run_patterns_build": run_patterns_build_impl,
    "read_file": read_file_impl,
}

# --- LLM LOOP -----------------------------------------------------------------


openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def call_model_with_pattern_tools(user_message: str) -> None:
    global TOTAL_INPUT_TOKENS, TOTAL_OUTPUT_TOKENS, CALLS

    system_prompt = (
        "You are an AI software architect using Decodifier, a compiler for AI-generated software.\n\n"
        "You MUST follow these rules:\n"
        "- Never edit Python files directly.\n"
        "- Only create or modify YAML specs under patterns/specs/ using write_spec_file.\n"
        "- After changing specs, call run_patterns_build to compile them into backend code.\n"
        "- You may call read_file to inspect generated code (read-only) to verify the result.\n\n"
        "Goal for this session:\n"
        "- Use Decodifier patterns to create a small FastAPI backend that exposes:\n"
        "  * GET /health\n"
        "  * POST /users\n"
        "  * GET /users/{id}\n"
        "- Use existing backend.http_endpoint patterns if available.\n"
        "- At the end, summarize which spec files you created/modified and which routes "
        "should now exist in the backend.\n"
    )

    messages: list[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    while True:
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=PATTERN_TOOLS,
            tool_choice="auto",
        )

        # --- token accounting ---
        usage = response.usage
        if usage is not None:
            # chat.completions usage fields
            in_tokens = getattr(usage, "prompt_tokens", 0)
            out_tokens = getattr(usage, "completion_tokens", 0)
            TOTAL_INPUT_TOKENS += in_tokens
            TOTAL_OUTPUT_TOKENS += out_tokens
            CALLS += 1
            print(
                f"\n[USAGE] call {CALLS}: "
                f"in={in_tokens}, out={out_tokens}, total={usage.total_tokens}"
            )
        # -------------------------

        message = response.choices[0].message

        # If the model is done and not calling tools, print its final answer.
        if not message.tool_calls:
            print("\nMODEL (final):\n")
            print(message.content)
            break

        # Record the assistant message that *initiated* the tool calls.
        messages.append(
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [tc.model_dump() for tc in message.tool_calls],
            }
        )

        # Execute each tool call and feed results back into the conversation.
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            args_json = tool_call.function.arguments

            try:
                args: Dict[str, Any] = (
                    json.loads(args_json) if isinstance(args_json, str) else args_json
                )
            except Exception:
                args = {}

            print(f"\n[TOOL CALL] {tool_name}({args})")

            impl = TOOL_IMPLS.get(tool_name)
            if impl is None:
                tool_output = {"error": f"Unknown tool: {tool_name}"}
            else:
                try:
                    tool_output = impl(**args)
                except Exception as exc:  # pragma: no cover
                    tool_output = {"error": str(exc)}

            tool_output_str = json.dumps(tool_output, indent=2, default=str)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": tool_output_str,
                }
            )

    # after loop finishes (model is done), print totals
    print("\n=== PATTERN RUN TOKEN USAGE ===")
    print(f"calls:          {CALLS}")
    print(f"input tokens:   {TOTAL_INPUT_TOKENS}")
    print(f"output tokens:  {TOTAL_OUTPUT_TOKENS}")
    print(f"total tokens:   {TOTAL_INPUT_TOKENS + TOTAL_OUTPUT_TOKENS}")


if __name__ == "__main__":
    # You can tweak this message to test different behaviors.
    user_prompt = (
        "Use the available tools to create or update the necessary patterns/specs so that "
        "the backend exposes GET /health, POST /users, and GET /users/{id}. "
        "Follow the rules in the system prompt strictly."
    )
    call_model_with_pattern_tools(user_prompt)
