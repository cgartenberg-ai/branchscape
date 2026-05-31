# branchscape/council_server/data_test.py
import os, unittest
from council_server import data

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

class DataLoaderTest(unittest.TestCase):
    def test_load_strips_window_prefix_and_parses(self):
        d = data.load_js_global(os.path.join(DATA_DIR, "branches.js"), "BRANCH_DATA")
        self.assertIn("branches", d)
        b = d["branches"][0]
        for k in ("name", "lat", "lon", "dep"):
            self.assertIn(k, b)

    def test_dataset_loads_all_globals(self):
        ds = data.Dataset(DATA_DIR)
        self.assertGreater(len(ds.branches), 100)
        self.assertGreater(len(ds.tracts), 100)
        self.assertGreater(len(ds.income), 10)
        self.assertIn("tracts", ds.cra)

if __name__ == "__main__":
    unittest.main()
