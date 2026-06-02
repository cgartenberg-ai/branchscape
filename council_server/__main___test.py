# branchscape/council_server/__main___test.py
import inspect, unittest
from council_server import __main__ as entry
from council_server.llm import ClaudeClient

class ReportBudgetTest(unittest.TestCase):
    def test_report_gets_a_larger_token_budget_than_a_conversational_turn(self):
        # The decision memo is a full 6-section document; at the per-turn default
        # (1500) it truncated mid-sentence. The report client must request more.
        per_turn_default = inspect.signature(ClaudeClient).parameters["max_tokens"].default
        self.assertEqual(per_turn_default, 1500, "guard: per-turn default assumption")
        self.assertGreater(entry.REPORT_MAX_TOKENS, per_turn_default,
                           "the decision-memo call needs more tokens than a single turn")

if __name__ == "__main__":
    unittest.main()
