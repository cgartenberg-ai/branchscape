# branchscape/council_server/envfile_test.py
import os, tempfile, unittest
from council_server import envfile

class ParseEnvTest(unittest.TestCase):
    def test_parses_key_value_and_ignores_comments_and_blanks(self):
        d = envfile.parse_env("# comment\n\nANTHROPIC_API_KEY=sk-ant-abc\nFOO = bar \n")
        self.assertEqual(d["ANTHROPIC_API_KEY"], "sk-ant-abc")
        self.assertEqual(d["FOO"], "bar")
        self.assertNotIn("# comment", d)

    def test_strips_quotes_and_export_prefix(self):
        d = envfile.parse_env('export KEY="quoted value"\nOTHER=\'single\'\n')
        self.assertEqual(d["KEY"], "quoted value")
        self.assertEqual(d["OTHER"], "single")

    def test_load_env_does_not_override_existing_by_default(self):
        with tempfile.TemporaryDirectory() as dd:
            p = os.path.join(dd, ".env")
            open(p, "w").write("COUNCIL_TEST_VAR=from_file\n")
            os.environ.pop("COUNCIL_TEST_VAR", None)
            envfile.load_env(p)
            self.assertEqual(os.environ["COUNCIL_TEST_VAR"], "from_file")
            os.environ["COUNCIL_TEST_VAR"] = "from_shell"
            envfile.load_env(p)  # no override
            self.assertEqual(os.environ["COUNCIL_TEST_VAR"], "from_shell")
            os.environ.pop("COUNCIL_TEST_VAR", None)

    def test_load_env_overrides_empty_or_whitespace_existing(self):
        # An empty (or whitespace-only) existing env var must NOT shadow the real
        # .env value — this is the demo-day blocker: a shell that exports
        # ANTHROPIC_API_KEY="" once silently suppressed the key from .env.
        with tempfile.TemporaryDirectory() as dd:
            p = os.path.join(dd, ".env")
            open(p, "w").write("COUNCIL_TEST_VAR=from_file\n")
            os.environ["COUNCIL_TEST_VAR"] = ""           # present but empty
            envfile.load_env(p)
            self.assertEqual(os.environ["COUNCIL_TEST_VAR"], "from_file")
            os.environ["COUNCIL_TEST_VAR"] = "   "         # whitespace-only
            envfile.load_env(p)
            self.assertEqual(os.environ["COUNCIL_TEST_VAR"], "from_file")
            os.environ.pop("COUNCIL_TEST_VAR", None)

    def test_load_env_missing_file_is_noop(self):
        self.assertEqual(envfile.load_env("/no/such/.env"), {})

if __name__ == "__main__":
    unittest.main()
