# branchscape/council_server/app.py
import json, os, threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from functools import partial
from council_server.hub import EventHub
from council_server.data import Dataset

ROOT = os.path.join(os.path.dirname(__file__), "..")  # branchscape/

def format_sse(event):
    return "data: " + json.dumps(event) + "\n\n"

class CouncilHandler(SimpleHTTPRequestHandler):
    hub = None          # set in serve()
    runner = None       # callable(mandate) -> None, runs a deliberation; set in serve()

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, *a):
        pass  # quiet; SSE keep-alives would spam the console

    def do_GET(self):
        if self.path.split("?")[0] == "/events":
            return self._sse()
        return super().do_GET()

    def _sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        q = self.hub.subscribe()
        try:
            while True:
                evt = q.get()
                self.wfile.write(format_sse(evt).encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            self.hub.unsubscribe(q)

    def do_POST(self):
        if self.path.split("?")[0] != "/control":
            self.send_error(404); return
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        action = body.get("action")
        if action == "start":
            mandate = body.get("mandate", "")
            threading.Thread(target=self.runner, args=(mandate,), daemon=True).start()
        elif action == "replay":
            import os
            from council_server.record import replay_events
            path = body.get("path") or os.path.join(ROOT, "runs", "golden.jsonl")
            speed = float(body.get("speed", 1.0))
            def play():
                if not os.path.exists(path):
                    self.hub.publish({"type": "error", "data": {"message": "no golden run to replay"}})
                    return
                for evt in replay_events(path, speed=speed):
                    self.hub.publish(evt)
            threading.Thread(target=play, daemon=True).start()
        self.send_response(204); self.end_headers()

def serve(port, runner_factory, host="127.0.0.1"):
    hub = EventHub()
    dataset = Dataset(os.path.join(ROOT, "data"))
    runner = runner_factory(hub, dataset)
    CouncilHandler.hub = hub
    CouncilHandler.runner = staticmethod(runner)
    httpd = ThreadingHTTPServer((host, port), CouncilHandler)
    print(f"COUNCIL LIVE on http://{host}:{port}/council.html  (Ctrl-C to stop)")
    httpd.serve_forever()
