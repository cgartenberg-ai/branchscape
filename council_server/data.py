# branchscape/council_server/data.py
import json, os, re

def load_js_global(path, var):
    """Read a `window.<var> = <json>;` file and return the parsed JSON."""
    s = open(path, encoding="utf-8").read().strip()
    s = re.sub(r"^window\." + re.escape(var) + r"\s*=\s*", "", s)
    s = s.rstrip().rstrip(";")
    return json.loads(s)

class Dataset:
    """Loads the BRANCHSCAPE data globals for server-side querying."""
    def __init__(self, data_dir):
        bd = load_js_global(os.path.join(data_dir, "branches.js"), "BRANCH_DATA")
        self.branches = bd["branches"]
        self.years = bd.get("years", [])
        self.tracts = load_js_global(os.path.join(data_dir, "tracts.js"), "TRACTS")
        self.cra = load_js_global(os.path.join(data_dir, "cra_tract.js"), "CRA_TRACT")
        self.income = load_js_global(os.path.join(data_dir, "income.js"), "INCOME_DATA")
