# LLM Integration Guide

1. Start the engine: `uvicorn engine.app.main:app --reload`.
2. Load tools from `decodifier.tool_registry.DECODIFIER_TOOLS`.
3. When the model emits tool calls, dispatch via `decodifier.client.handle_decodifier_tool_call`.
4. Feed tool outputs back into the model.

See `clients/openai_demo/decodifier_openai_demo.py` for a working example.
