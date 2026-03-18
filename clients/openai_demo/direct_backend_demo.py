import json
import os
from typing import Any, Dict

from openai import OpenAI

# Match your decode_test path
DECO_ROOT = os.environ.get(
    "DECODIFIER_ROOT",
    "/mnt/c/Users/jwmar/desktop/decode_test/decodifier",
)
OPENAI_MODEL = os.environ.get("DECODIFIER_MODEL", "gpt-4.1-mini")

TOTAL_INPUT_TOKENS = 0
TOTAL_OUTPUT_TOKENS = 0
CALLS = 0

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def _abs_path(rel_path: str) -> str:
    return os.path.join(DECO_ROOT, rel_path)


def write_file_impl(path: str, content: str) -> Dict[str, Any]:
    abs_path = _abs_path(path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(content)
    return {"status": "ok", "path": path, "bytes": len(content)}


def read_file_impl(path: str) -> Dict[str, Any]:
    abs_path = _abs_path(path)
    if not os.path.exists(abs_path):
        return {"exists": False, "path": path}
    with open(abs_path, "r", encoding="utf-8") as f:
        return {"exists": True, "path": path, "content": f.read()}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write a text file relative to the project root. Use this to create the FastAPI app code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path like 'backend/api/app_direct.py'",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full file content to write.",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the project to verify what you wrote.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                },
                "required": ["path"],
            },
        },
    },
]

TOOL_IMPLS = {
    "write_file": write_file_impl,
    "read_file": read_file_impl,
}


def run_direct_backend_demo() -> None:
    global TOTAL_INPUT_TOKENS, TOTAL_OUTPUT_TOKENS, CALLS

    system_prompt = """
You are a senior Python backend developer.

Your job: create a small FastAPI backend BY WRITING CODE DIRECTLY (no compiler).

Requirements:
- Create one file at backend/api/app_direct.py
- It must define a FastAPI FastAPI app or APIRouter mounted at /api with:
    * GET /health  -> returns JSON { "status": "ok" }
    * POST /users  -> accepts JSON { "username", "email" } and returns created user with an id
    * GET /users/{id} -> returns JSON with that user's data
- Use the write_file tool to write the file.
- Optionally use read_file to verify final content.
- At the end, summarize what you wrote.
"""

    messages: list[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Create the backend as described using write_file."},
    ]

    while True:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        usage = resp.usage
        if usage is not None:
            in_tokens = getattr(usage, "prompt_tokens", 0)
            out_tokens = getattr(usage, "completion_tokens", 0)
            TOTAL_INPUT_TOKENS += in_tokens
            TOTAL_OUTPUT_TOKENS += out_tokens
            CALLS += 1
            print(
                f"\n[USAGE] call {CALLS}: "
                f"in={in_tokens}, out={out_tokens}, total={usage.total_tokens}"
            )

        msg = resp.choices[0].message

        if not msg.tool_calls:
            print("\nMODEL (final):\n")
            print(msg.content)
            break

        messages.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
            }
        )

        for tc in msg.tool_calls:
            name = tc.function.name
            args_json = tc.function.arguments
            args: Dict[str, Any] = (
                json.loads(args_json) if isinstance(args_json, str) else args_json
            )
            print(f"\n[TOOL CALL] {name}({list(args.keys())})")

            impl = TOOL_IMPLS[name]
            result = impl(**args)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": name,
                    "content": json.dumps(result),
                }
            )

    print("\n=== DIRECT RUN TOKEN USAGE ===")
    print(f"calls:          {CALLS}")
    print(f"input tokens:   {TOTAL_INPUT_TOKENS}")
    print(f"output tokens:  {TOTAL_OUTPUT_TOKENS}")
    print(f"total tokens:   {TOTAL_INPUT_TOKENS + TOTAL_OUTPUT_TOKENS}")


if __name__ == "__main__":
    run_direct_backend_demo()
