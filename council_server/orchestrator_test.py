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

def fake_with_empty_chair():
    """Reproduces the live-run stall: specialists vote, but the Chair's synthesis
    turn returns EMPTY text (in the real run it spent the turn on tool calls)."""
    line = lambda t: {"text": t, "tool_calls": []}
    s = []
    for _ in range(5): s.append(line("Gathering."))
    for _ in range(5): s.append(line("My position is tract 4705."))
    for _ in range(3): s.append(line("Rebuttal."))
    for _ in range(5):
        s.append({"text": "", "tool_calls": [
            {"id": "v", "name": "cast_vote",
             "input": {"zone": "04013004705", "stance": "support", "rationale": "underserved"}}]})
    s.append(line(""))  # chair: EMPTY synthesis -> the bug
    return FakeClaude(s)

class _BoomClient:
    """Raises on every turn — simulates a real API/stream failure mid-run."""
    def stream_agent_turn(self, **kw):
        raise RuntimeError("simulated API failure")
        yield  # pragma: no cover (makes this a generator)

class _ToolCapture:
    """Records the `tools` arg of each turn; always returns empty text, no tools."""
    def __init__(self): self.tools_seen = []
    def stream_agent_turn(self, system, messages, tools, model=None):
        self.tools_seen.append(list(tools or []))
        yield ("final", {"text": "ok", "tool_calls": []})

class _RecordingClient:
    """Wraps an inner client, recording each turn's last user instruction while
    delegating the actual scripted behavior (so votes still get cast)."""
    def __init__(self, inner): self.inner = inner; self.instructions = []
    def stream_agent_turn(self, system, messages, tools, model=None):
        last_user = next((m["content"] for m in reversed(messages)
                          if m.get("role") == "user"), "")
        self.instructions.append(last_user)
        yield from self.inner.stream_agent_turn(
            system=system, messages=messages, tools=tools, model=model)

class _SystemCapture:
    """Records the `system` of every turn; returns benign text, no tools."""
    def __init__(self): self.systems = []
    def stream_agent_turn(self, system, messages, tools, model=None):
        self.systems.append(system)
        yield ("final", {"text": "ok", "tool_calls": []})

class _MsgCapture:
    """Records the FULL messages list of every turn while delegating behavior to an
    inner client — so a test can prove a presenter's mid-run message reaches a later
    agent's prompt."""
    def __init__(self, inner): self.inner = inner; self.messages_seen = []
    def stream_agent_turn(self, system, messages, tools, model=None):
        self.messages_seen.append(list(messages))
        yield from self.inner.stream_agent_turn(
            system=system, messages=messages, tools=tools, model=model)

class OrchestratorTest(unittest.TestCase):
    def test_profile_threads_into_every_agent_system_prompt(self):
        # The presenter's bank profile must reach EVERY agent (incl. the Chair),
        # so the whole council reasons AS that specific bank.
        ds = Dataset(DATA_DIR)
        cap = _SystemCapture()
        profile = {"name": "Sonoran Ag & Trust", "type": "rural agricultural",
                   "region": "West Valley", "values": ["agricultural lending"]}
        Orchestrator(ds, cap, emit=lambda e: None).run("m", profile)
        self.assertTrue(cap.systems, "agents should have run")
        self.assertTrue(all("Sonoran Ag & Trust" in s for s in cap.systems),
                        "every agent turn must carry the bank profile")

    def test_no_profile_leaves_role_prompts_unchanged(self):
        ds = Dataset(DATA_DIR)
        cap = _SystemCapture()
        Orchestrator(ds, cap, emit=lambda e: None).run("m")  # no profile
        from council_server.agents import ROLE_PROMPTS
        self.assertEqual(cap.systems[0], ROLE_PROMPTS["market"])  # first turn = market, verbatim

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

    def test_verdict_is_VISIBLE_even_when_chair_text_is_empty(self):
        # THE live-run stall: empty chair synthesis must NOT produce a blank verdict.
        ds = Dataset(DATA_DIR)
        events = []
        Orchestrator(ds, fake_with_empty_chair(), emit=events.append).run("m")
        verdict = next(e for e in events if e["type"] == "verdict")
        self.assertTrue(verdict["data"]["text"].strip(),
                        "verdict text must be non-empty (derive a summary if the chair is silent)")
        self.assertIn("tally", verdict["data"])
        self.assertGreaterEqual(verdict["data"]["tally"].get("support", 0), 1)

    def test_run_ALWAYS_concludes_even_if_every_turn_raises(self):
        ds = Dataset(DATA_DIR)
        events = []
        Orchestrator(ds, _BoomClient(), emit=events.append).run("m")
        types = [e["type"] for e in events]
        self.assertIn("error", types, "a failed turn must surface a recorded error")
        self.assertIn("verdict", types, "verdict must ALWAYS be emitted")
        self.assertEqual(events[-1]["type"], "run_end", "run_end must ALWAYS be last")

    def test_chair_instruction_surfaces_plurality_and_grants_overrule(self):
        # The Chair's judgment prevails: its synthesis turn must be told the vote
        # plurality AND be explicitly allowed to overrule it (while acknowledging it).
        ds = Dataset(DATA_DIR)
        rec = _RecordingClient(fake_for_full_run())  # all 5 votes -> tract …2345
        Orchestrator(ds, rec, emit=lambda e: None).run("m")
        chair_instruction = rec.instructions[-1]      # the final (chair) turn
        self.assertIn("2345", chair_instruction, "chair must see the plurality tract")
        self.assertIn("overrule", chair_instruction.lower())
        self.assertIn("acknowledge", chair_instruction.lower())

    def test_chair_synthesis_turn_gets_no_tools(self):
        ds = Dataset(DATA_DIR)
        cap = _ToolCapture()
        Orchestrator(ds, cap, emit=lambda e: None).run("m")
        # 18 specialist turns (gather5+positions5+crossExam3+vote5) see tools; the
        # final (chair) turn must see an EMPTY tool list.
        self.assertEqual(cap.tools_seen[-1], [], "chair synthesis turn must be tool-free")
        self.assertTrue(len(cap.tools_seen[0]) > 0, "specialist turns DO get tools")

    def test_presenter_inject_reaches_the_live_deliberation(self):
        # THE presenter/audience redirect: a message injected mid-run must (1) surface as
        # a visible room_inject event, (2) fold into the shared transcript as a directive,
        # and (3) actually reach a LATER agent's prompt so the council responds to it.
        ds = Dataset(DATA_DIR)
        cap = _MsgCapture(fake_for_full_run())
        orch = Orchestrator(ds, cap, emit=lambda e: None)
        events = []
        ROOM = "weight rural community access far higher than deposit growth"
        state = {"fired": False}
        def emit(e):
            events.append(e)
            # inject exactly once, mid-run, as the 'positions' beat opens
            if (e.get("type") == "phase_change" and e["data"]["beat"] == "positions"
                    and not state["fired"]):
                state["fired"] = True
                orch.inject(ROOM)
        orch.emit = emit
        orch.run("Open one new branch in Maricopa")

        # (1) a visible event so the HUD can show the redirect
        self.assertTrue(any(e["type"] == "room_inject" and ROOM in e["data"]["text"]
                            for e in events), "a room_inject event must be emitted")
        # (2) folded into the shared transcript as a [THE ROOM] directive
        self.assertTrue(any("[THE ROOM" in (m.get("content") or "") and ROOM in m.get("content", "")
                            for m in orch.transcript), "room message must enter the transcript")
        # (3) a later agent turn actually SEES it in its messages
        seen_after = [msgs for msgs in cap.messages_seen
                      if any("[THE ROOM" in (m.get("content") or "") for m in msgs)]
        self.assertTrue(seen_after, "at least one agent turn after the redirect must include it")

if __name__ == "__main__":
    unittest.main()
