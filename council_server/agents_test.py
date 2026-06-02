# branchscape/council_server/agents_test.py
import os, unittest
from council_server.data import Dataset
from council_server.fake_llm import FakeClaude
from council_server.agents import AgentRunner, ROLE_PROMPTS, AGENT_IDS, build_profile_preamble

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

class _SystemCapture:
    """Records the `system` of each turn; returns benign text, no tools."""
    def __init__(self): self.systems = []
    def stream_agent_turn(self, system, messages, tools, model=None):
        self.systems.append(system)
        yield ("final", {"text": "ok", "tool_calls": []})

class AgentsTest(unittest.TestCase):
    def test_six_roles_defined(self):
        self.assertEqual(set(AGENT_IDS),
                         {"chair", "market", "risk", "community", "realestate", "devil"})
        for a in AGENT_IDS:
            self.assertTrue(ROLE_PROMPTS[a].strip())

    def test_run_turn_resolves_a_tool_call_then_finalizes(self):
        ds = Dataset(DATA_DIR)
        fake = FakeClaude(scripted=[
            {"text": "Let me check deposits.",
             "tool_calls": [{"id": "t1", "name": "query_data", "input": {"metric": "branch_count"}}]},
            {"text": "With 600+ branches, coverage is dense.", "tool_calls": []},
        ])
        events = []
        runner = AgentRunner("market", ds, fake, emit=events.append)
        result = runner.run_turn(transcript=[{"role": "user", "content": "go"}])
        kinds = [e["type"] for e in events]
        self.assertIn("tool_call", kinds)
        self.assertIn("tool_result", kinds)
        self.assertTrue(result["text"].startswith("With 600+"))

    def test_build_profile_preamble_blank_when_no_profile(self):
        self.assertEqual(build_profile_preamble(None), "")
        self.assertEqual(build_profile_preamble({}), "")

    def test_build_profile_preamble_carries_bank_identity(self):
        pre = build_profile_preamble({
            "name": "Cactus Community Bank", "type": "community", "asset_size": "$850M",
            "region": "East Valley", "values": ["CRA leadership", "small-business lending"]})
        for needle in ["Cactus Community Bank", "community", "East Valley", "CRA leadership"]:
            self.assertIn(needle, pre)

    def test_run_turn_prepends_profile_preamble_to_system(self):
        ds = Dataset(DATA_DIR)
        cap = _SystemCapture()
        AgentRunner("market", ds, cap, emit=lambda e: None,
                    profile_preamble="BANKCTX-XYZ").run_turn(
            transcript=[{"role": "user", "content": "go"}])
        self.assertIn("BANKCTX-XYZ", cap.systems[0])           # profile injected
        self.assertIn(ROLE_PROMPTS["market"], cap.systems[0])  # role prompt preserved

    def test_run_turn_emits_vote_cast_when_agent_votes(self):
        ds = Dataset(DATA_DIR)
        fake = FakeClaude(scripted=[
            {"text": "Voting now.",
             "tool_calls": [{"id": "v1", "name": "cast_vote",
                             "input": {"zone": "04013012345", "stance": "support", "rationale": "gap"}}]},
        ])
        events = []
        runner = AgentRunner("market", ds, fake, emit=events.append)
        result = runner.run_turn(transcript=[{"role": "user", "content": "vote"}])
        self.assertTrue(any(e["type"] == "vote_cast" for e in events))
        self.assertEqual(result["votes"][0]["stance"], "support")

if __name__ == "__main__":
    unittest.main()
