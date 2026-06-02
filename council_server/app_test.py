# branchscape/council_server/app_test.py
import json, threading, http.client, unittest
from http.server import ThreadingHTTPServer
from council_server.app import format_sse, CouncilHandler
from council_server.hub import EventHub

class SseFormatTest(unittest.TestCase):
    def test_format_sse_is_data_line_plus_blank(self):
        out = format_sse({"type": "error", "ts": 1.0, "agent": None, "data": {}})
        self.assertTrue(out.startswith("data: "))
        self.assertTrue(out.endswith("\n\n"))
        self.assertIn('"type": "error"', out)

class HealthEndpointTest(unittest.TestCase):
    """The page probes /health to decide live-vs-demo; a real server must answer 200."""
    def test_health_returns_200_ok_json(self):
        CouncilHandler.hub = EventHub()
        CouncilHandler.runner = staticmethod(lambda *a, **k: None)
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), CouncilHandler)
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            c.request("GET", "/health")
            r = c.getresponse()
            self.assertEqual(r.status, 200)
            self.assertEqual(json.loads(r.read()).get("status"), "ok")
        finally:
            httpd.shutdown(); httpd.server_close()

if __name__ == "__main__":
    unittest.main()
