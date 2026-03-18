import json
import os
from typing import Any, Dict

from openai import OpenAI

from decodifier.client import DeCodifierClient, handle_decodifier_tool_call
from decodifier.tool_registry import DECODIFIER_TOOLS


openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
decodifier_client = DeCodifierClient(base_url="http://127.0.0.1:8000")


def call_model_with_tools(user_message: str) -> None:
    system_prompt = (
        "You are a developer assistant with access to DeCodifier, a backend that manages code "
        "projects on disk. Use the tools to inspect and modify files instead of guessing."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    while True:
        response = openai_client.chat.completions.create(
            model="gpt-5-nano",
            messages=messages,
            tools=DECODIFIER_TOOLS,
            tool_choice="auto",
        )

        message = response.choices[0].message

        if not message.tool_calls:
            print("\nMODEL (final):", message.content)
            break

        messages.append(
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [tc.model_dump() for tc in message.tool_calls],
            }
        )

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

            tool_output = handle_decodifier_tool_call(decodifier_client, tool_name, args)
            tool_output_str = json.dumps(tool_output, indent=2, default=str)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": tool_output_str,
                }
            )


if __name__ == "__main__":
    user_prompt = (
        "You have access to a DeCodifier backend that can read, write, and modify files "
        "in the 'core_backend' project using tools. "
        "Your task: create a small, working Python service in the core_backend project.\n\n"
        "Requirements:\n"
        "1. Create a new package folder 'scratch/todo_service'.\n"
        "2. Inside it, create:\n"
        "   - __init__.py (can be empty)\n"
        "   - models.py defining a simple Todo item dataclass with id, title, done: bool.\n"
        "   - storage.py with in-memory list-based CRUD functions (add_todo, list_todos, mark_done).\n"
        "   - api.py exposing a FastAPI router with /todos GET and POST, and /todos/{id}/done PUT.\n"
        "3. If there is an existing FastAPI app in the project, register this router under /api.\n"
        "4. Use DeCodifier tools to create and edit files. Do not just describe the code; actually write it.\n"
        "5. At the end, summarize exactly what files you created or modified, with paths."
    )
    call_model_with_tools(user_prompt)
