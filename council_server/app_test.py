# branchscape/council_server/app_test.py
import unittest
from council_server.app import format_sse

class SseFormatTest(unittest.TestCase):
    def test_format_sse_is_data_line_plus_blank(self):
        out = format_sse({"type": "error", "ts": 1.0, "agent": None, "data": {}})
        self.assertTrue(out.startswith("data: "))
        self.assertTrue(out.endswith("\n\n"))
        self.assertIn('"type": "error"', out)

if __name__ == "__main__":
    unittest.main()
