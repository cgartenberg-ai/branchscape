# branchscape/council_server/tools_test.py
import os, unittest
from council_server.data import Dataset
from council_server import tools

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

class ToolsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ds = Dataset(DATA_DIR)

    def test_schemas_list_has_query_data_and_cast_vote(self):
        names = {t["name"] for t in tools.schemas()}
        self.assertEqual(names, {"query_data", "cast_vote"})

    def test_query_data_deposits_returns_summary_number(self):
        out = tools.dispatch(self.ds, "query_data", {"metric": "total_deposits"})
        self.assertIn("value", out)
        self.assertGreater(out["value"], 0)

    def test_query_data_underserved_returns_ranked_tracts(self):
        out = tools.dispatch(self.ds, "query_data", {"metric": "underserved_tracts", "limit": 5})
        self.assertEqual(len(out["rows"]), 5)
        self.assertIn("geoid", out["rows"][0])

    def test_cast_vote_echoes_structured_vote(self):
        out = tools.dispatch(self.ds, "cast_vote",
                             {"zone": "04013012345", "stance": "support", "rationale": "wide gap"})
        self.assertEqual(out["stance"], "support")
        self.assertEqual(out["zone"], "04013012345")

    def test_unknown_tool_raises(self):
        with self.assertRaises(KeyError):
            tools.dispatch(self.ds, "nope", {})

if __name__ == "__main__":
    unittest.main()
