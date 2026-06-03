# branchscape/council_server/app_test.py
import json, threading, http.client, unittest
from http.server import ThreadingHTTPServer
from council_server.app import format_sse, CouncilHandler
from council_server.hub import EventHub
from council_server.gate import RunGate

def _boot():
    """Start the handler on an ephemeral port; return (httpd, port)."""
    CouncilHandler.hub = EventHub()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), CouncilHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]

def _post(port, payload):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    c.request("POST", "/control", body=json.dumps(payload),
              headers={"Content-Type": "application/json"})
    return c.getresponse().status

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

class InjectControlTest(unittest.TestCase):
    """The presenter redirect: POST /control {action:inject} must forward the text to
    the running runner (which hands it to the live Orchestrator)."""
    def test_inject_action_forwards_text_to_the_runner(self):
        CouncilHandler.hub = EventHub()
        injected = []
        def runner(*a, **k):
            pass
        runner.inject = lambda text: injected.append(text)
        CouncilHandler.runner = staticmethod(runner)
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), CouncilHandler)
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            c.request("POST", "/control",
                      json.dumps({"action": "inject", "text": "weight community access higher"}),
                      {"Content-Type": "application/json"})
            r = c.getresponse()
            self.assertEqual(r.status, 204)
            r.read()
        finally:
            httpd.shutdown(); httpd.server_close()
        self.assertEqual(injected, ["weight community access higher"],
                         "the inject action must reach runner.inject")

class PasscodeGateTest(unittest.TestCase):
    """A public/tunneled endpoint must reject 'start' without the right passcode."""
    def setUp(self):
        self._saved_gate = CouncilHandler.gate
        self._started = []
        CouncilHandler.runner = staticmethod(lambda *a, **k: self._started.append(a))

    def tearDown(self):
        CouncilHandler.gate = self._saved_gate

    def test_start_rejected_without_passcode_and_accepted_with_it(self):
        CouncilHandler.gate = RunGate(passcode="open-sesame")
        httpd, port = _boot()
        try:
            self.assertEqual(_post(port, {"action": "start", "mandate": "m"}), 403)
            self.assertEqual(_post(port, {"action": "start", "mandate": "m",
                                          "passcode": "wrong"}), 403)
            self.assertEqual(_post(port, {"action": "start", "mandate": "m",
                                          "passcode": "open-sesame"}), 204)
        finally:
            httpd.shutdown(); httpd.server_close()

if __name__ == "__main__":
    unittest.main()
