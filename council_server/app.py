# branchscape/council_server/app.py
import json, os, threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from functools import partial
from council_server.hub import EventHub
from council_server.data import Dataset
from council_server.gate import RunGate

ROOT = os.path.join(os.path.dirname(__file__), "..")  # branchscape/

def format_sse(event):
    return "data: " + json.dumps(event) + "\n\n"

class CouncilHandler(SimpleHTTPRequestHandler):
    hub = None          # set in serve()
    runner = None       # callable(mandate, profile) -> None, runs a deliberation; set in serve()
    gate = RunGate()    # passcode + concurrency guard; replaced from env in serve()

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, *a):
        pass  # quiet; SSE keep-alives would spam the console

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/events":
            return self._sse()
        if path == "/health":
            return self._health()
        return super().do_GET()

    def _health(self):
        # Lets the page detect a real council_server (vs a static host) and decide
        # whether to run live agents or fall back to the Phase-1 demo.
        body = json.dumps({"status": "ok", "mode": "live"}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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
            # Guard real API spend on a public (tunneled/hosted) endpoint.
            if not self.gate.authorized(body.get("passcode")):
                self.send_response(403); self.end_headers(); return      # wrong/missing passcode
            if not self.gate.try_acquire():
                self.send_response(429); self.end_headers(); return      # at concurrency cap
            mandate = body.get("mandate", "")
            profile = body.get("profile")  # optional bank-profile dict from the setup panel
            def guarded():
                try:
                    self.runner(mandate, profile)
                finally:
                    self.gate.release()  # free the slot whether the run finished or errored
            threading.Thread(target=guarded, daemon=True).start()
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
        elif action == "inject":
            # Presenter / "the room" steers the LIVE deliberation: forward the text to the
            # running Orchestrator, which folds it into the debate at the next turn boundary.
            text = (body.get("text") or "").strip()
            forward = getattr(self.runner, "inject", None)
            if text and callable(forward):
                forward(text)
        self.send_response(204); self.end_headers()

def serve(port, runner_factory, host="127.0.0.1"):
    hub = EventHub()
    dataset = Dataset(os.path.join(ROOT, "data"))
    runner = runner_factory(hub, dataset)
    CouncilHandler.hub = hub
    CouncilHandler.runner = staticmethod(runner)
    # Public-exposure guard (matters when tunneled/hosted; harmless locally):
    #   COUNCIL_PASSCODE      — if set, the page must pass ?key=<it> to convene
    #   COUNCIL_MAX_CONCURRENT— cap on simultaneous deliberations (default 2)
    gate = RunGate(os.environ.get("COUNCIL_PASSCODE"),
                   os.environ.get("COUNCIL_MAX_CONCURRENT", 2))
    CouncilHandler.gate = gate
    if gate.passcode:
        print(f"🔒 passcode required to convene (max {gate.max_concurrent} concurrent).")
    httpd = ThreadingHTTPServer((host, port), CouncilHandler)
    print(f"COUNCIL LIVE on http://{host}:{port}/council.html  (Ctrl-C to stop)")
    httpd.serve_forever()
