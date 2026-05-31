# branchscape/council_server/llm_test.py
import unittest
from council_server.fake_llm import FakeClaude

class FakeClaudeTest(unittest.TestCase):
    def test_streams_text_chunks_then_returns_message(self):
        fake = FakeClaude(scripted=[
            {"text": "Buckeye looks underserved.", "tool_calls": []},
        ])
        chunks, result = [], None
        for kind, payload in fake.stream_agent_turn(system="s", messages=[], tools=[]):
            if kind == "thinking":
                chunks.append(payload)
            elif kind == "final":
                result = payload
        self.assertTrue("".join(chunks).startswith("Buckeye"))
        self.assertEqual(result["text"], "Buckeye looks underserved.")
        self.assertEqual(result["tool_calls"], [])

    def test_emits_tool_calls_in_final(self):
        fake = FakeClaude(scripted=[
            {"text": "Let me check.", "tool_calls": [
                {"id": "t1", "name": "query_data", "input": {"metric": "deposits"}}]},
        ])
        result = None
        for kind, payload in fake.stream_agent_turn(system="s", messages=[], tools=[]):
            if kind == "final":
                result = payload
        self.assertEqual(result["tool_calls"][0]["name"], "query_data")

if __name__ == "__main__":
    unittest.main()
