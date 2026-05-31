# branchscape/council_server/llm.py
import os

class ClaudeClient:
    """Thin wrapper over the anthropic Messages API with streaming + tool use.
    Mirrors FakeClaude.stream_agent_turn so the orchestrator is client-agnostic."""
    def __init__(self, model="claude-sonnet-4-5", api_key=None):
        import anthropic  # imported lazily so tests never need the SDK/key
        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self._model = model

    def stream_agent_turn(self, system, messages, tools, model=None):
        text_parts, tool_calls = [], []
        with self._client.messages.stream(
            model=model or self._model,
            max_tokens=1024,
            system=system,
            messages=messages,
            tools=tools or [],
        ) as stream:
            for event in stream:
                if event.type == "content_block_delta" and getattr(event.delta, "text", None):
                    text_parts.append(event.delta.text)
                    yield ("thinking", event.delta.text)
            final = stream.get_final_message()
        for block in final.content:
            if block.type == "tool_use":
                tool_calls.append({"id": block.id, "name": block.name, "input": block.input})
        yield ("final", {"text": "".join(text_parts), "tool_calls": tool_calls})
