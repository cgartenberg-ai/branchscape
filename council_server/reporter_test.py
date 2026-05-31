# branchscape/council_server/reporter_test.py
import os, tempfile, unittest
from council_server import reporter
from council_server.fake_llm import FakeClaude

EVENTS = [
    {"type": "run_start", "data": {"mandate": "Open one branch in Maricopa"}},
    {"type": "phase_change", "data": {"beat": "gather"}},
    {"type": "agent_message", "agent": "market", "data": {"text": "Tract 1017 has the widest deposit gap."}},
    {"type": "tool_call", "agent": "market", "data": {"name": "query_data", "input": {"metric": "underserved_tracts"}}},
    {"type": "tool_result", "agent": "market", "data": {"name": "query_data", "result": {"value": 42}}},
    {"type": "phase_change", "data": {"beat": "vote"}},
    {"type": "vote_cast", "agent": "market", "data": {"zone": "04013001017", "stance": "support", "rationale": "gap"}},
    {"type": "vote_cast", "agent": "devil", "data": {"zone": "04013001017", "stance": "conditional", "rationale": "watch competition"}},
    {"type": "verdict", "agent": "chair", "data": {"text": "Recommend tract 1017.", "tally": {"support": 1, "conditional": 1}}},
    {"type": "run_end", "data": {}},
]

class TranscriptTest(unittest.TestCase):
    def test_transcript_contains_mandate_message_vote_verdict(self):
        md = reporter.build_transcript(EVENTS)
        self.assertIn("Open one branch in Maricopa", md)   # mandate
        self.assertIn("widest deposit gap", md)            # agent words
        self.assertIn("query_data", md)                    # tool query shown
        self.assertIn("support", md)                       # vote shown
        self.assertIn("Recommend tract 1017", md)          # verdict shown
        self.assertIn("Market Analyst", md)                # display name, not 'market'

class ReportTest(unittest.TestCase):
    def test_build_report_uses_one_llm_call(self):
        fake = FakeClaude([{"text": "# Decision Memo\n## Recommendation\nTract 1017.", "tool_calls": []}])
        out = reporter.build_report("the transcript", fake)
        self.assertIn("Decision Memo", out)

class ArtifactsTest(unittest.TestCase):
    def test_write_artifacts_writes_both_files_and_returns_urls(self):
        with tempfile.TemporaryDirectory() as d:
            fake = FakeClaude([{"text": "# Decision Memo\nfoo", "tool_calls": []}])
            urls = reporter.write_artifacts(EVENTS, d, "run-123", fake)
            self.assertTrue(os.path.exists(os.path.join(d, "run-123-transcript.md")))
            self.assertTrue(os.path.exists(os.path.join(d, "run-123-report.md")))
            self.assertEqual(urls["transcript"], "/runs/run-123-transcript.md")
            self.assertEqual(urls["report"], "/runs/run-123-report.md")

if __name__ == "__main__":
    unittest.main()
