# branchscape/council_server/fake_llm.py
class FakeClaude:
    """Deterministic stand-in for the Claude client used in tests.
    `scripted` is a list of {text, tool_calls}; one per call to stream_agent_turn."""
    def __init__(self, scripted):
        self._scripted = list(scripted)
        self._i = 0

    def stream_agent_turn(self, system, messages, tools, model=None):
        turn = self._scripted[self._i]
        self._i += 1
        # stream the text in a few chunks to mimic token streaming
        text = turn["text"]
        mid = max(1, len(text) // 2)
        for chunk in (text[:mid], text[mid:]):
            if chunk:
                yield ("thinking", chunk)
        yield ("final", {"text": text, "tool_calls": turn.get("tool_calls", [])})
