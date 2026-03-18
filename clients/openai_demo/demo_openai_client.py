import os

from openai import OpenAI

from decodifier.tool_registry import DECODIFIER_TOOLS


client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

response = client.chat.completions.create(
    model="gpt-5-nano",
    messages=[{"role": "user", "content": "List my DeCodifier projects."}],
    tools=DECODIFIER_TOOLS,
    tool_choice="auto",
)

print(response.choices[0].message)
