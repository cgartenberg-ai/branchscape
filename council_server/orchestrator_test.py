# branchscape/council_server/orchestrator_test.py
import os, unittest
from council_server.data import Dataset
from council_server.fake_llm import FakeClaude
from council_server.orchestrator import Orchestrator

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

def fake_for_full_run():
    # FakeClaude pops one scripted turn per stream call, in call order.
    line = lambda t: {"text": t, "tool_calls": []}
    scripted = []
    for _ in range(5): scripted.append(line("Gathering."))   # 5 specialists gather
    for _ in range(5): scripted.append(line("My position."))  # 5 specialists positions
    for _ in range(3): scripted.append(line("Rebuttal."))     # crossExam: devil, risk, market
    for _ in range(5):                                         # 5 specialists cast votes
        scripted.append({"text": "Voting.", "tool_calls": [
            {"id": "v", "name": "cast_vote",
             "input": {"zone": "04013012345", "stance": "support", "rationale": "r"}}]})
    scripted.append(line("The council recommends tract 12345 at moderate confidence; caveat noted."))
    return FakeClaude(scripted)

class OrchestratorTest(unittest.TestCase):
    def test_full_run_emits_all_beats_and_a_verdict(self):
        ds = Dataset(DATA_DIR)
        events = []
        orch = Orchestrator(ds, fake_for_full_run(), emit=events.append)
        orch.run("Open one new branch in Maricopa — balance growth with community access")
        beats = [e["data"]["beat"] for e in events if e["type"] == "phase_change"]
        self.assertEqual(beats, ["mandate", "gather", "positions", "crossExam", "vote"])
        self.assertTrue(any(e["type"] == "vote_cast" for e in events))
        self.assertTrue(any(e["type"] == "verdict" for e in events))
        self.assertEqual(events[0]["type"], "run_start")
        self.assertEqual(events[-1]["type"], "run_end")

if __name__ == "__main__":
    unittest.main()
