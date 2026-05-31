# THE COUNCIL: Live — Phase 2a+2b Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the deterministic Phase-1 brain with REAL Claude agents that reason, query data, argue, and emerge a recommendation — streamed live onto the existing council-of-light stage. This plan delivers P2a (prove the streaming pipe with one real agent) and P2b (the full facilitated 6-agent deliberation over loaded data, with record/replay fallback).

**Architecture:** A local Python server (`council_server/`, stdlib HTTP + the `anthropic` SDK only) runs an Orchestrator that drives 5 beats and, per beat, spawns one streaming Claude Messages-API conversation per agent. Agents call tools (`query_data`, `cast_vote`) resolved server-side. Every event (phase_change / agent_thinking / agent_message / tool_call / tool_result / vote_cast / verdict / error) is pushed to the browser over Server-Sent Events AND appended to a JSONL run log. The browser (`council/live.js`) renders events into the existing `council/ui.js` HUD. A saved "golden" log can be replayed through the identical renderer for an offline-safe, bulletproof fallback.

**Tech Stack:** Python 3.13 (stdlib `http.server` + `threading` + `unittest`; no Flask/FastAPI), `anthropic` SDK 0.75 (already installed), vanilla browser JS (EventSource for SSE), the existing deck.gl/maplibre stage. No new JS deps.

---

## Scope

- **This plan = Phase 2a + 2b only.** P2c (live `web_search` + `map_action` drawing) and P2d (presenter inject / call-the-question / mode toggle / record golden run for public build) are **separate later plans**, written after the core runs.
- Spec: `branchscape/docs/superpowers/specs/2026-05-31-the-council-live-phase2-design.md`.
- Branch: `design/the-council` (Phase 1 is committed; this builds alongside it and demotes it to a fallback later).

## Environment facts (verified 2026-05-31)
- `python3` = 3.13.3; `anthropic` = 0.75.0 installed; `pip` available; `ANTHROPIC_API_KEY` NOT in shell (set before live runs).
- Data shapes (for `query_data`):
  - `data/branches.js` → `window.BRANCH_DATA = {region, source, deposit_units, years:[...], summary, branches:[{name, lat, lon, dep:{ "YYYY": thousands }}]}`
  - `data/cra_tract.js` → `window.CRA_TRACT = {year, tracts:{ geoid:{amt, n} }}`
  - `data/income.js` → `window.INCOME_DATA = [{zip, lat, lon, income}]`
  - `data/tracts.js` → `window.TRACTS = { geoid:[lon, lat] }`
  - The `.js` files are `window.NAME = <json>;` — the loader strips the `window.NAME=` prefix + trailing `;` and `json.loads` the rest.

## Testing approach (read before starting)
- **Python server logic** → stdlib `unittest`, run `python3 -m unittest discover -s council_server -p "*_test.py"`. Python does NOT have node's teardown segfault, so exit codes are reliable here.
- **Claude calls are mocked in tests.** No test calls the real API. A `FakeClaude` yields canned streaming/tool-use events so the orchestrator is fully testable offline/keyless. Real API is exercised only in the manual live-verification steps.
- **Browser rendering** → manual, identity-gated preview. Before trusting ANY browser reading: assert `document.title === 'THE COUNCIL — BRANCHSCAPE Act 2'` and the URL is the council page. The preview server caches hard → for final confirmation prefer a **user hard-refresh (⌘⇧R)**. A real end-to-end run (streamed thoughts + a real tool call + a vote + a verdict) is **required evidence before claiming a slice works** — never write "verified" without machine-read proof on the correct page.
- **JS logic** (event-dispatch reducer) → the existing zero-dep harness `council/_harness.js` via `./run-tests.sh`.

## Naming contract (keep exact across tasks)
- SSE event types (string `type` field): `phase_change`, `agent_thinking`, `agent_message`, `tool_call`, `tool_result`, `vote_cast`, `verdict`, `error`, `run_start`, `run_end`.
- Event envelope: `{ "type": <str>, "ts": <float>, "agent": <id|null>, "data": {...} }`. `agent` is one of the 6 ids or null.
- Agent ids (from Phase 1 `council/agents.js`): `chair`, `market`, `risk`, `community`, `realestate`, `devil`.
- Beat ids: `mandate`, `gather`, `positions`, `crossExam`, `vote`.
- Tool names: `query_data`, `cast_vote`.
- HTTP routes: `GET /events` (SSE), `POST /control` (`{action:"start"|"call_question", mandate?}`), plus static file serving for everything else.
- Python package: `council_server/` with modules `data.py`, `tools.py`, `agents.py`, `orchestrator.py`, `record.py`, `app.py`, and `__main__.py` (entry).
- Browser global: `CouncilLive` (in `council/live.js`).

---

# PHASE 2a — Prove the pipe

Goal of P2a: a real Claude agent's tokens stream from the server, over SSE, into the council caption, live. Smallest thing that proves key + streaming + transport + render all work.

## Task 1: Python package + data loader

**Files:**
- Create: `branchscape/council_server/__init__.py` (empty)
- Create: `branchscape/council_server/data.py`
- Create: `branchscape/council_server/data_test.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd branchscape && python3 -m unittest council_server.data_test -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'council_server.data'`.

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd branchscape && python3 -m unittest council_server.data_test -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add council_server/__init__.py council_server/data.py council_server/data_test.py
git commit -m "feat(council-live): python package + data loader over BRANCHSCAPE globals"
```

---

## Task 2: SSE event hub (in-memory pub/sub)

A thread-safe broker: the orchestrator publishes event dicts; each connected SSE client drains a queue. Pure Python, fully testable without HTTP.

**Files:**
- Create: `branchscape/council_server/hub.py`
- Create: `branchscape/council_server/hub_test.py`

- [ ] **Step 1: Write the failing test**

```python
# branchscape/council_server/hub_test.py
import unittest
from council_server.hub import EventHub

class HubTest(unittest.TestCase):
    def test_subscriber_receives_published_events(self):
        hub = EventHub()
        q = hub.subscribe()
        hub.publish({"type": "phase_change", "data": {"beat": "gather"}})
        evt = q.get(timeout=1)
        self.assertEqual(evt["type"], "phase_change")
        self.assertIn("ts", evt)  # hub stamps ts

    def test_multiple_subscribers_all_receive(self):
        hub = EventHub()
        a, b = hub.subscribe(), hub.subscribe()
        hub.publish({"type": "error", "data": {}})
        self.assertEqual(a.get(timeout=1)["type"], "error")
        self.assertEqual(b.get(timeout=1)["type"], "error")

    def test_unsubscribe_stops_delivery(self):
        hub = EventHub()
        q = hub.subscribe()
        hub.unsubscribe(q)
        hub.publish({"type": "error", "data": {}})
        self.assertTrue(q.empty())

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd branchscape && python3 -m unittest council_server.hub_test -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'council_server.hub'`.

- [ ] **Step 3: Write minimal implementation**

```python
# branchscape/council_server/hub.py
import queue, threading, time

class EventHub:
    """Thread-safe fan-out of event dicts to all current subscribers."""
    def __init__(self):
        self._subs = set()
        self._lock = threading.Lock()

    def subscribe(self):
        q = queue.Queue()
        with self._lock:
            self._subs.add(q)
        return q

    def unsubscribe(self, q):
        with self._lock:
            self._subs.discard(q)

    def publish(self, event):
        if "ts" not in event:
            event["ts"] = time.time()
        event.setdefault("agent", None)
        event.setdefault("data", {})
        with self._lock:
            subs = list(self._subs)
        for q in subs:
            q.put(event)
        return event
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd branchscape && python3 -m unittest council_server.hub_test -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add council_server/hub.py council_server/hub_test.py
git commit -m "feat(council-live): thread-safe SSE event hub with tests"
```

---

## Task 3: Claude client wrapper + FakeClaude (the test seam)

One narrow interface the rest of the code depends on, so tests never touch the network. `stream_agent_turn()` yields `("thinking", text)` chunks and returns the final assembled message + any tool calls.

**Files:**
- Create: `branchscape/council_server/llm.py`
- Create: `branchscape/council_server/fake_llm.py`
- Create: `branchscape/council_server/llm_test.py`

- [ ] **Step 1: Write the failing test (drives the FakeClaude contract)**

```python
# branchscape/council_server/llm_test.py
import unittest
from council_server.fake_llm import FakeClaude

class FakeClaudeTest(unittest.TestCase):
    def test_streams_text_chunks_then_returns_message(self):
        fake = FakeClaude(scripted=[
            {"text": "Buckeye looks underserved.", "tool_calls": []},
        ])
        chunks, result = [], None
        for kind, payload in fake.stream_agent_turn(system="s", messages=[], tools=[]):
            if kind == "thinking":
                chunks.append(payload)
            elif kind == "final":
                result = payload
        self.assertTrue("".join(chunks).startswith("Buckeye"))
        self.assertEqual(result["text"], "Buckeye looks underserved.")
        self.assertEqual(result["tool_calls"], [])

    def test_emits_tool_calls_in_final(self):
        fake = FakeClaude(scripted=[
            {"text": "Let me check.", "tool_calls": [
                {"id": "t1", "name": "query_data", "input": {"metric": "deposits"}}]},
        ])
        result = None
        for kind, payload in fake.stream_agent_turn(system="s", messages=[], tools=[]):
            if kind == "final":
                result = payload
        self.assertEqual(result["tool_calls"][0]["name"], "query_data")

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd branchscape && python3 -m unittest council_server.llm_test -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'council_server.fake_llm'`.

- [ ] **Step 3: Write the FakeClaude + the real wrapper**

```python
# branchscape/council_server/fake_llm.py
class FakeClaude:
    """Deterministic stand-in for the Claude client used in tests.
    `scripted` is a list of {text, tool_calls}; one per call to stream_agent_turn."""
    def __init__(self, scripted):
        self._scripted = list(scripted)
        self._i = 0

    def stream_agent_turn(self, system, messages, tools, model=None):
        turn = self._scripted[self._i]
        self._i += 1
        # stream the text in a few chunks to mimic token streaming
        text = turn["text"]
        mid = max(1, len(text) // 2)
        for chunk in (text[:mid], text[mid:]):
            if chunk:
                yield ("thinking", chunk)
        yield ("final", {"text": text, "tool_calls": turn.get("tool_calls", [])})
```

```python
# branchscape/council_server/llm.py
import os

class ClaudeClient:
    """Thin wrapper over the anthropic Messages API with streaming + tool use.
    Mirrors FakeClaude.stream_agent_turn so the orchestrator is client-agnostic."""
    def __init__(self, model="claude-sonnet-4-5", api_key=None):
        import anthropic  # imported lazily so tests never need the SDK/key
        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self._model = model

    def stream_agent_turn(self, system, messages, tools, model=None):
        text_parts, tool_calls = [], []
        with self._client.messages.stream(
            model=model or self._model,
            max_tokens=1024,
            system=system,
            messages=messages,
            tools=tools or [],
        ) as stream:
            for event in stream:
                if event.type == "content_block_delta" and getattr(event.delta, "text", None):
                    text_parts.append(event.delta.text)
                    yield ("thinking", event.delta.text)
            final = stream.get_final_message()
        for block in final.content:
            if block.type == "tool_use":
                tool_calls.append({"id": block.id, "name": block.name, "input": block.input})
        yield ("final", {"text": "".join(text_parts), "tool_calls": tool_calls})
```

> Model id note: `claude-sonnet-4-5` is the assumed default; if the SDK/account reports a different current id during live verification, update the default in `llm.py` only. Tests never use it.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd branchscape && python3 -m unittest council_server.llm_test -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add council_server/llm.py council_server/fake_llm.py council_server/llm_test.py
git commit -m "feat(council-live): Claude client wrapper + FakeClaude test seam"
```

---

## Task 4: HTTP app — static files + SSE + control (P2a single-agent path)

Serves the existing static site AND adds `/events` (SSE) and `/control`. For P2a, `start` runs ONE agent turn through the hub so we can see real streaming. (The full orchestrator replaces this in P2b.)

**Files:**
- Create: `branchscape/council_server/app.py`
- Create: `branchscape/council_server/__main__.py`
- Create: `branchscape/council_server/app_test.py`

- [ ] **Step 1: Write the failing test (SSE formatting + routing, no real server socket)**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd branchscape && python3 -m unittest council_server.app_test -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'council_server.app'`.

- [ ] **Step 3: Implement the app**

```python
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
        if body.get("action") == "start":
            mandate = body.get("mandate", "")
            threading.Thread(target=self.runner, args=(mandate,), daemon=True).start()
        self.send_response(204); self.end_headers()

def serve(port, runner_factory, host="127.0.0.1"):
    hub = EventHub()
    dataset = Dataset(os.path.join(ROOT, "data"))
    runner = runner_factory(hub, dataset)
    handler = partial(CouncilHandler)
    CouncilHandler.hub = hub
    CouncilHandler.runner = staticmethod(runner)
    httpd = ThreadingHTTPServer((host, port), handler)
    print(f"COUNCIL LIVE on http://{host}:{port}/council.html  (Ctrl-C to stop)")
    httpd.serve_forever()
```

```python
# branchscape/council_server/__main__.py
import os, sys
from council_server.app import serve
from council_server.llm import ClaudeClient
from council_server.fake_llm import FakeClaude

def make_runner(hub, dataset):
    # P2a: one real agent turn streamed to the hub. Replaced by the orchestrator in P2b.
    use_fake = os.environ.get("COUNCIL_FAKE") == "1"
    client = FakeClaude(scripted=[{"text": "Streaming a real thought about Maricopa branch siting.", "tool_calls": []}]) if use_fake else ClaudeClient()
    def runner(mandate):
        hub.publish({"type": "run_start", "data": {"mandate": mandate}})
        hub.publish({"type": "phase_change", "data": {"beat": "positions"}})
        for kind, payload in client.stream_agent_turn(
            system="You are the Market Analyst on a bank branch-siting council. One vivid sentence.",
            messages=[{"role": "user", "content": mandate or "Where should we open the next branch in Maricopa County?"}],
            tools=[],
        ):
            if kind == "thinking":
                hub.publish({"type": "agent_thinking", "agent": "market", "data": {"text": payload}})
            else:
                hub.publish({"type": "agent_message", "agent": "market", "data": {"text": payload["text"]}})
        hub.publish({"type": "run_end", "data": {}})
    return runner

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8078
    serve(port, make_runner)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd branchscape && python3 -m unittest council_server.app_test -v`
Expected: PASS (1 test).

- [ ] **Step 5: Smoke-test the server with the FAKE client (no key, no network)**

```bash
cd branchscape && COUNCIL_FAKE=1 python3 -m council_server 8078 &
sleep 1
# subscribe in the background, fire a start, expect streamed events
( curl -sN http://127.0.0.1:8078/events & sleep 0.3; \
  curl -s -X POST http://127.0.0.1:8078/control -d '{"action":"start","mandate":"test"}'; sleep 1; kill %1 ) 2>/dev/null
```
Expected: SSE lines including `"type": "run_start"`, several `"type": "agent_thinking"`, one `"type": "agent_message"`, `"type": "run_end"`. Then `kill %1` (the server). If you see those event types, the pipe works end to end with zero network.

- [ ] **Step 6: Commit**

```bash
git add council_server/app.py council_server/__main__.py council_server/app_test.py
git commit -m "feat(council-live): HTTP app with SSE + control, P2a single-agent streaming (fake-verified)"
```

---

## Task 5: Browser live client + caption streaming (P2a end-to-end)

`council/live.js` subscribes to `/events` and renders streamed thinking into the caption via the existing `CouncilUI`. A small pure reducer (`applyEvent`) is unit-tested with the node harness; the EventSource wiring is verified in the browser.

**Files:**
- Create: `branchscape/council/live.js`
- Create: `branchscape/council/live.test.js`
- Modify: `branchscape/council.html` (load live.js; add a `?live` boot path)
- Modify: `branchscape/council/ui.js` (add `appendThinking` for token-by-token caption)

- [ ] **Step 1: Write the failing test for the pure reducer**

```javascript
// branchscape/council/live.test.js
const assert = require('node:assert');
const { test, report } = require('./_harness.js');
const { applyEvent, initialState } = require('./live.js');

test('agent_thinking appends streamed text for the active agent', () => {
  let s = initialState();
  s = applyEvent(s, { type: 'phase_change', data: { beat: 'positions' } });
  s = applyEvent(s, { type: 'agent_thinking', agent: 'market', data: { text: 'Buck' } });
  s = applyEvent(s, { type: 'agent_thinking', agent: 'market', data: { text: 'eye' } });
  assert.strictEqual(s.activeAgent, 'market');
  assert.strictEqual(s.caption, 'Buckeye');
  assert.strictEqual(s.beat, 'positions');
});

test('agent_message finalizes the line and a new agent_thinking resets caption', () => {
  let s = initialState();
  s = applyEvent(s, { type: 'agent_thinking', agent: 'market', data: { text: 'hi' } });
  s = applyEvent(s, { type: 'agent_message', agent: 'market', data: { text: 'hi there' } });
  assert.strictEqual(s.lastMessage.text, 'hi there');
  s = applyEvent(s, { type: 'agent_thinking', agent: 'risk', data: { text: 'X' } });
  assert.strictEqual(s.activeAgent, 'risk');
  assert.strictEqual(s.caption, 'X');
});

report();
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd branchscape && node council/live.test.js`
Expected: FAIL — `Cannot find module './live.js'`. (End the test file with `report();`.)

- [ ] **Step 3: Implement live.js (dual-mode: reducer is testable in node, EventSource only in browser)**

```javascript
// branchscape/council/live.js
(function (global) {
  function initialState() {
    return { beat: null, activeAgent: null, caption: '', lastMessage: null, votes: [], verdict: null };
  }
  // Pure: (state, event) -> state. No DOM. This is the single source of truth.
  function applyEvent(state, evt) {
    const s = Object.assign({}, state);
    switch (evt.type) {
      case 'phase_change': s.beat = evt.data.beat; break;
      case 'agent_thinking':
        if (evt.agent !== s.activeAgent) { s.activeAgent = evt.agent; s.caption = ''; }
        s.caption = (s.caption || '') + (evt.data.text || '');
        break;
      case 'agent_message':
        s.activeAgent = evt.agent;
        s.lastMessage = { agent: evt.agent, text: evt.data.text };
        s.caption = evt.data.text;
        break;
      case 'vote_cast': s.votes = s.votes.concat([evt.data]); break;
      case 'verdict': s.verdict = evt.data; break;
      default: break;
    }
    return s;
  }

  // Browser-only: connect SSE and render each event into the existing HUD.
  function connect(opts) {
    let state = initialState();
    const es = new EventSource('/events');
    es.onmessage = (m) => {
      const evt = JSON.parse(m.data);
      state = applyEvent(state, evt);
      render(evt, state);
    };
    es.onerror = () => { if (opts && opts.onError) opts.onError(); };
    return {
      start: (mandate) => fetch('/control', { method: 'POST', body: JSON.stringify({ action: 'start', mandate }) }),
      callQuestion: () => fetch('/control', { method: 'POST', body: JSON.stringify({ action: 'call_question' }) }),
      state: () => state,
    };
  }
  function render(evt, state) {
    if (typeof CouncilUI === 'undefined') return;
    if (evt.type === 'phase_change') CouncilUI.setPhase('LIVE · ' + state.beat.toUpperCase());
    if (evt.type === 'agent_thinking') CouncilUI.setActiveSpeaker(state.activeAgent, state.caption);
    if (evt.type === 'agent_message') CouncilUI.setActiveSpeaker(evt.agent, evt.data.text);
  }

  const api = { initialState, applyEvent, connect };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else global.CouncilLive = api;
})(typeof window !== 'undefined' ? window : globalThis);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd branchscape && node council/live.test.js`
Expected: `RESULT tests=2 pass=2 fail=0` in `council/.last-test-result`.

- [ ] **Step 5: Wire `?live` into council.html**

In `council.html`, add after the existing `council/director.js` script tag:
```html
  <script src="council/live.js"></script>
```
Replace the boot `<script>` block with a mode switch:
```javascript
    CouncilMap.initMap();
    CouncilUI.mount();
    const params = new URLSearchParams(location.search);
    if (params.has('live')) {
      const live = CouncilLive.connect({ onError: () => CouncilUI.setPhase('LIVE · connection lost') });
      window.__council = live; // presenter handle
      CouncilUI.setPhase('LIVE · ready — POST start to begin');
    } else {
      Director.wireControls();
      Director.start('Open one new branch in Maricopa — balance deposit growth with community access');
    }
```

- [ ] **Step 6: Manual end-to-end verification (FAKE client first, then REAL)**

FAKE (no key): 
```bash
cd branchscape && COUNCIL_FAKE=1 python3 -m council_server 8078
```
Open `http://localhost:8078/council.html?live` (hard-refresh). In the browser console run `__council.start('Where should we open the next branch?')`.
**Identity gate first:** confirm `document.title === 'THE COUNCIL — BRANCHSCAPE Act 2'`.
**Expected:** the Market Analyst node lights up and the caption fills in token-by-token, then settles to the final sentence. Screenshot it.

REAL (needs key): `export ANTHROPIC_API_KEY=sk-...` then `python3 -m council_server 8078`, same steps.
**Expected:** a *different*, genuinely-generated sentence streams in. This is the P2a proof. (User hard-refresh recommended for the authoritative check.)

- [ ] **Step 7: Commit**

```bash
git add council/live.js council/live.test.js council.html council/ui.js
git commit -m "feat(council-live): browser SSE client + live caption streaming (P2a end-to-end)"
```

---

**✅ P2a milestone:** a real Claude agent streams a live thought onto the stage. Stop and demo this to the user before continuing — it's the proof the whole approach works.

---

# PHASE 2b — Facilitated 6-agent deliberation over loaded data

Goal of P2b: the full 5-beat, 6-agent deliberation. Agents reason over real data via `query_data`, post positions, cross-examine, and the Chair synthesizes a vote — all streamed. Every run is recorded; a golden run can be replayed offline.

## Task 6: `query_data` + `cast_vote` tools

**Files:**
- Create: `branchscape/council_server/tools.py`
- Create: `branchscape/council_server/tools_test.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd branchscape && python3 -m unittest council_server.tools_test -v`
Expected: FAIL — `No module named 'council_server.tools'`.

- [ ] **Step 3: Implement the tools**

```python
# branchscape/council_server/tools.py
import math

def schemas():
    """Anthropic tool schemas exposed to every agent."""
    return [
        {
            "name": "query_data",
            "description": "Query the Maricopa County banking dataset (FDIC deposits, "
                           "CRA small-business lending, IRS income by ZIP, census tracts).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "enum": [
                        "total_deposits", "branch_count", "underserved_tracts",
                        "high_income_tracts", "tract_detail"]},
                    "geoid": {"type": "string", "description": "tract id, for tract_detail"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["metric"],
            },
        },
        {
            "name": "cast_vote",
            "description": "Record your vote for where to open the branch.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "zone": {"type": "string", "description": "census tract geoid"},
                    "stance": {"type": "string", "enum": ["support", "conditional", "oppose"]},
                    "rationale": {"type": "string"},
                },
                "required": ["zone", "stance", "rationale"],
            },
        },
    ]

def _haversine_km(a_lat, a_lon, b_lat, b_lon):
    R = 6371.0
    dlat = math.radians(b_lat - a_lat); dlon = math.radians(b_lon - a_lon)
    s = (math.sin(dlat/2)**2 + math.cos(math.radians(a_lat))*math.cos(math.radians(b_lat))*math.sin(dlon/2)**2)
    return 2*R*math.asin(min(1, math.sqrt(s)))

def _nearest_income(ds, lon, lat):
    best, val = 1e9, 0
    for p in ds.income:
        d = _haversine_km(lat, lon, p["lat"], p["lon"])
        if d < best: best, val = d, p["income"]
    return val

def _tract_rows(ds):
    """Build a per-tract summary used by the ranking metrics (skips 98xx special tracts)."""
    rows = []
    for geoid, (lon, lat) in ds.tracts.items():
        if int(str(geoid)[-6:]) >= 980000:
            continue
        cra = ds.cra["tracts"].get(geoid, {})
        rows.append({
            "geoid": geoid, "lon": lon, "lat": lat,
            "income": _nearest_income(ds, lon, lat),
            "cra_amt": cra.get("amt", 0),
        })
    return rows

def dispatch(ds, name, args):
    if name == "query_data":
        return _query_data(ds, args)
    if name == "cast_vote":
        return {"zone": args["zone"], "stance": args["stance"], "rationale": args.get("rationale", "")}
    raise KeyError(name)

def _query_data(ds, args):
    metric = args["metric"]; limit = int(args.get("limit", 5))
    if metric == "total_deposits":
        total = sum((b["dep"].get("2024", 0) for b in ds.branches))
        return {"metric": metric, "value": total, "units": "USD thousands"}
    if metric == "branch_count":
        return {"metric": metric, "value": len(ds.branches)}
    if metric == "underserved_tracts":
        rows = sorted(_tract_rows(ds), key=lambda r: (r["cra_amt"], r["income"]))[:limit]
        return {"metric": metric, "rows": rows}
    if metric == "high_income_tracts":
        rows = sorted(_tract_rows(ds), key=lambda r: -r["income"])[:limit]
        return {"metric": metric, "rows": rows}
    if metric == "tract_detail":
        g = args.get("geoid"); lonlat = ds.tracts.get(g)
        if not lonlat: return {"metric": metric, "error": "unknown geoid"}
        lon, lat = lonlat; cra = ds.cra["tracts"].get(g, {})
        return {"metric": metric, "geoid": g, "income": _nearest_income(ds, lon, lat),
                "cra_amt": cra.get("amt", 0)}
    return {"metric": metric, "error": "unknown metric"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd branchscape && python3 -m unittest council_server.tools_test -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add council_server/tools.py council_server/tools_test.py
git commit -m "feat(council-live): query_data + cast_vote tools over real data"
```

---

## Task 7: Agent role prompts + AgentRunner (turn with tool resolution)

`AgentRunner.run_turn()` streams an agent's thinking, resolves any tool calls (looping the tool results back per the Messages API tool-use protocol), and returns the final message + structured tool effects. Tested with FakeClaude scripted to emit a tool call then a final answer.

**Files:**
- Create: `branchscape/council_server/agents.py`
- Create: `branchscape/council_server/agents_test.py`

- [ ] **Step 1: Write the failing test**

```python
# branchscape/council_server/agents_test.py
import os, unittest
from council_server.data import Dataset
from council_server.fake_llm import FakeClaude
from council_server.agents import AgentRunner, ROLE_PROMPTS, AGENT_IDS

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

class AgentsTest(unittest.TestCase):
    def test_six_roles_defined(self):
        self.assertEqual(set(AGENT_IDS),
                         {"chair", "market", "risk", "community", "realestate", "devil"})
        for a in AGENT_IDS:
            self.assertTrue(ROLE_PROMPTS[a].strip())

    def test_run_turn_resolves_a_tool_call_then_finalizes(self):
        ds = Dataset(DATA_DIR)
        fake = FakeClaude(scripted=[
            {"text": "Let me check deposits.",
             "tool_calls": [{"id": "t1", "name": "query_data", "input": {"metric": "branch_count"}}]},
            {"text": "With 600+ branches, coverage is dense.", "tool_calls": []},
        ])
        events = []
        runner = AgentRunner("market", ds, fake, emit=events.append)
        result = runner.run_turn(transcript=[{"role": "user", "content": "go"}])
        kinds = [e["type"] for e in events]
        self.assertIn("tool_call", kinds)
        self.assertIn("tool_result", kinds)
        self.assertTrue(result["text"].startswith("With 600+"))

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd branchscape && python3 -m unittest council_server.agents_test -v`
Expected: FAIL — `No module named 'council_server.agents'`.

- [ ] **Step 3: Implement roles + runner**

```python
# branchscape/council_server/agents.py
from council_server import tools

AGENT_IDS = ["chair", "market", "risk", "community", "realestate", "devil"]

ROLE_PROMPTS = {
    "market": "You are the MARKET ANALYST on a community bank's branch-siting council for "
        "Maricopa County, AZ. You care about deposit-growth opportunity: household income, "
        "demand, and where deposits are under-captured. Use query_data to ground every claim "
        "in real numbers. Be concise (2-3 sentences), cite figures, and engage other members' points.",
    "risk": "You are the RISK OFFICER. You care about competition and saturation — too many "
        "nearby branches means cannibalization. Use query_data. Push back when others are "
        "over-optimistic. 2-3 sentences, cite figures.",
    "community": "You are the COMMUNITY / CRA OFFICER. You champion underbanked, lower-income "
        "tracts and CRA credit. Use query_data (underserved_tracts). Argue for mission, not just "
        "margin. 2-3 sentences, cite figures.",
    "realestate": "You are the REAL-ESTATE SCOUT. You weigh site cost and feasibility — "
        "higher-income areas cost more to enter. Use query_data. 2-3 sentences, cite figures.",
    "devil": "You are the DEVIL'S ADVOCATE. Your job is to ATTACK the current front-runner with "
        "real evidence — find its weakest dimension via query_data and force the council to price "
        "it in. Be sharp but fair. 2-3 sentences.",
    "chair": "You are the CHAIR. You synthesize the council's discussion into a single "
        "recommendation, preserving any dissent. When asked to call the vote, state the "
        "recommended tract and the confidence, and name the key caveat. 3-4 sentences.",
}

MODEL_FOR = {"chair": "claude-sonnet-4-5", "devil": "claude-sonnet-4-5"}  # others may use a faster tier in P2d

class AgentRunner:
    """Runs one agent's turn: stream thinking, resolve tool calls, return final message."""
    def __init__(self, agent_id, dataset, client, emit, model=None):
        self.id = agent_id; self.ds = dataset; self.client = client
        self.emit = emit; self.model = model

    def run_turn(self, transcript, max_tool_rounds=3):
        system = ROLE_PROMPTS[self.id]
        messages = list(transcript)
        for _ in range(max_tool_rounds + 1):
            text, tool_calls = "", []
            for kind, payload in self.client.stream_agent_turn(
                system=system, messages=messages, tools=tools.schemas(), model=self.model):
                if kind == "thinking":
                    self.emit({"type": "agent_thinking", "agent": self.id, "data": {"text": payload}})
                else:
                    text, tool_calls = payload["text"], payload["tool_calls"]
            if not tool_calls:
                self.emit({"type": "agent_message", "agent": self.id, "data": {"text": text}})
                return {"text": text, "votes": []}
            # resolve tool calls, append assistant tool_use + user tool_result, loop
            assistant_content = ([{"type": "text", "text": text}] if text else []) + [
                {"type": "tool_use", "id": tc["id"], "name": tc["name"], "input": tc["input"]} for tc in tool_calls]
            messages.append({"role": "assistant", "content": assistant_content})
            results = []
            votes = []
            for tc in tool_calls:
                self.emit({"type": "tool_call", "agent": self.id,
                           "data": {"name": tc["name"], "input": tc["input"]}})
                out = tools.dispatch(self.ds, tc["name"], tc["input"])
                self.emit({"type": "tool_result", "agent": self.id,
                           "data": {"name": tc["name"], "result": out}})
                if tc["name"] == "cast_vote":
                    votes.append(out)
                    self.emit({"type": "vote_cast", "agent": self.id, "data": out})
                results.append({"type": "tool_result", "tool_use_id": tc["id"],
                                "content": __import__("json").dumps(out)})
            messages.append({"role": "user", "content": results})
            if votes:
                return {"text": text, "votes": votes}
        return {"text": text, "votes": []}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd branchscape && python3 -m unittest council_server.agents_test -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add council_server/agents.py council_server/agents_test.py
git commit -m "feat(council-live): role prompts + AgentRunner with tool-use loop"
```

---

## Task 8: Recorder + Replayer

**Files:**
- Create: `branchscape/council_server/record.py`
- Create: `branchscape/council_server/record_test.py`

- [ ] **Step 1: Write the failing test**

```python
# branchscape/council_server/record_test.py
import json, os, tempfile, unittest
from council_server.record import Recorder, replay_events

class RecordTest(unittest.TestCase):
    def test_recorder_appends_jsonl_and_replay_reads_back(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "run.jsonl")
            rec = Recorder(path)
            rec.write({"type": "phase_change", "data": {"beat": "gather"}})
            rec.write({"type": "verdict", "data": {"zone": "x"}})
            evts = list(replay_events(path, sleep=lambda s: None))
            self.assertEqual([e["type"] for e in evts], ["phase_change", "verdict"])

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd branchscape && python3 -m unittest council_server.record_test -v`
Expected: FAIL — `No module named 'council_server.record'`.

- [ ] **Step 3: Implement**

```python
# branchscape/council_server/record.py
import json, time

class Recorder:
    """Appends every emitted event as one JSON line."""
    def __init__(self, path):
        self.path = path
        self._f = open(path, "a", encoding="utf-8")
    def write(self, event):
        self._f.write(json.dumps(event) + "\n"); self._f.flush()
    def close(self):
        try: self._f.close()
        except Exception: pass

def replay_events(path, sleep=time.sleep, speed=1.0):
    """Yield events from a JSONL run log, pausing by the original inter-event gaps."""
    prev = None
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line: continue
        evt = json.loads(line)
        ts = evt.get("ts")
        if prev is not None and ts is not None:
            gap = max(0.0, (ts - prev) / speed)
            if gap: sleep(min(gap, 3.0))  # cap any pause at 3s
        prev = ts
        yield evt
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd branchscape && python3 -m unittest council_server.record_test -v`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add council_server/record.py council_server/record_test.py
git commit -m "feat(council-live): JSONL recorder + timed replayer"
```

---

## Task 9: Orchestrator — the 5 beats

Drives the deliberation: seeds the transcript, runs `gather`/`positions` (parallel-capable), `crossExam` (sequential, agents see each other), and `vote` (Chair synthesizes). Emits every event through an `emit` callback (wired to hub+recorder in the app). Tested entirely with FakeClaude — no network.

**Files:**
- Create: `branchscape/council_server/orchestrator.py`
- Create: `branchscape/council_server/orchestrator_test.py`

- [ ] **Step 1: Write the failing test**

```python
# branchscape/council_server/orchestrator_test.py
import os, unittest
from council_server.data import Dataset
from council_server.fake_llm import FakeClaude
from council_server.orchestrator import Orchestrator

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

def fake_for_full_run():
    # 6 specialists gather (1 msg each) + 6 positions + a short crossExam + chair verdict.
    # FakeClaude pops one scripted turn per stream call, in call order. Keep them generic.
    line = lambda t: {"text": t, "tool_calls": []}
    scripted = []
    # gather (6) + positions (6) + crossExam (3) + vote: each agent cast_vote, then chair verdict
    for _ in range(6): scripted.append(line("Gathering."))
    for _ in range(6): scripted.append(line("My position."))
    for _ in range(3): scripted.append(line("Rebuttal."))
    for _ in range(5):  # 5 specialists cast votes
        scripted.append({"text": "Voting.", "tool_calls": [
            {"id": "v", "name": "cast_vote", "input": {"zone": "04013012345", "stance": "support", "rationale": "r"}}]})
    scripted.append(line("The council recommends tract 12345 at moderate confidence; caveat noted."))
    return FakeClaude(scripted)

class OrchestratorTest(unittest.TestCase):
    def test_full_run_emits_all_beats_and_a_verdict(self):
        ds = Dataset(DATA_DIR)
        events = []
        orch = Orchestrator(ds, fake_for_full_run(), emit=events.append)
        orch.run("Open one new branch in Maricopa — balance growth with community access")
        beats = [e["data"]["beat"] for e in events if e["type"] == "phase_change"]
        self.assertEqual(beats, ["mandate", "gather", "positions", "crossExam", "vote"])
        self.assertTrue(any(e["type"] == "vote_cast" for e in events))
        self.assertTrue(any(e["type"] == "verdict" for e in events))
        self.assertEqual(events[0]["type"], "run_start")
        self.assertEqual(events[-1]["type"], "run_end")

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd branchscape && python3 -m unittest council_server.orchestrator_test -v`
Expected: FAIL — `No module named 'council_server.orchestrator'`.

- [ ] **Step 3: Implement the orchestrator**

```python
# branchscape/council_server/orchestrator.py
from council_server.agents import AgentRunner, AGENT_IDS

SPECIALISTS = ["market", "risk", "community", "realestate", "devil"]

class Orchestrator:
    """Facilitated, Chair-driven 5-beat deliberation. Content within beats is emergent."""
    def __init__(self, dataset, client, emit):
        self.ds = dataset; self.client = client; self.emit = emit
        self.transcript = []   # shared chat all agents see
        self.votes = []

    def _runner(self, agent_id):
        return AgentRunner(agent_id, self.ds, self.client, emit=self.emit)

    def _say(self, agent_id, instruction):
        msgs = self.transcript + [{"role": "user", "content": instruction}]
        result = self._runner(agent_id).run_turn(msgs)
        if result["text"]:
            self.transcript.append({"role": "user",
                "content": f"[{agent_id}] {result['text']}"})
        self.votes.extend(result.get("votes", []))
        return result

    def _phase(self, beat):
        self.emit({"type": "phase_change", "data": {"beat": beat}})

    def run(self, mandate):
        self.emit({"type": "run_start", "data": {"mandate": mandate}})
        self._phase("mandate")
        self.transcript.append({"role": "user", "content": f"MANDATE: {mandate}"})

        self._phase("gather")
        for a in SPECIALISTS:
            self._say(a, f"{a}: gather the data you need with query_data and note one finding.")

        self._phase("positions")
        for a in SPECIALISTS:
            self._say(a, f"{a}: state your opening recommendation (a tract) with cited evidence.")

        self._phase("crossExam")
        for a in ["devil", "risk", "market"]:
            self._say(a, f"{a}: respond to the others — challenge or defend the front-runner.")

        self._phase("vote")
        for a in ["market", "risk", "community", "realestate", "devil"]:
            self._say(a, f"{a}: cast_vote now with your final stance and rationale.")
        chair = self._say("chair", "chair: call the vote. Synthesize one recommendation, "
                          "state confidence, preserve dissent.")
        self.emit({"type": "verdict", "agent": "chair",
                   "data": {"text": chair["text"], "votes": self.votes}})
        self.emit({"type": "run_end", "data": {}})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd branchscape && python3 -m unittest council_server.orchestrator_test -v`
Expected: PASS (1 test).

- [ ] **Step 5: Run the whole server test suite**

Run: `cd branchscape && python3 -m unittest discover -s council_server -p "*_test.py" -v`
Expected: all suites PASS (data, hub, llm, app, tools, agents, record, orchestrator).

- [ ] **Step 6: Commit**

```bash
git add council_server/orchestrator.py council_server/orchestrator_test.py
git commit -m "feat(council-live): 5-beat facilitated orchestrator (fake-Claude tested)"
```

---

## Task 10: Wire orchestrator into the app (real runner factory + recording + replay)

Replace the P2a single-agent runner with the orchestrator; record every run; add a replay route for offline/golden playback.

**Files:**
- Modify: `branchscape/council_server/__main__.py`
- Modify: `branchscape/council_server/app.py` (add `mode`/replay support to `/control`)
- Create: `branchscape/runs/.gitkeep`
- Modify: `branchscape/.gitignore` (ignore `runs/*.jsonl` except a golden one)

- [ ] **Step 1: Update the runner factory to use the orchestrator + recorder**

Replace `make_runner` in `council_server/__main__.py`:
```python
import os, sys, time
from council_server.app import serve
from council_server.llm import ClaudeClient
from council_server.fake_llm import FakeClaude
from council_server.orchestrator import Orchestrator
from council_server.record import Recorder

def make_runner(hub, dataset):
    use_fake = os.environ.get("COUNCIL_FAKE") == "1"
    def runner(mandate):
        # one recorder per run, named by wall-clock (passed in, not Date.now in JS)
        path = os.path.join(os.path.dirname(__file__), "..", "runs", f"run-{int(time.time())}.jsonl")
        rec = Recorder(path)
        def emit(evt):
            rec.write(hub.publish(evt))   # hub stamps ts + defaults, recorder persists the same dict
        client = FakeClaude(scripted=[{"text": "fake", "tool_calls": []}]*40) if use_fake else ClaudeClient()
        try:
            Orchestrator(dataset, client, emit).run(mandate)
        except Exception as e:
            hub.publish({"type": "error", "data": {"message": str(e)}})
        finally:
            rec.close()
    return runner

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8078
    serve(port, make_runner)
```

- [ ] **Step 2: Add replay to /control in app.py**

In `CouncilHandler.do_POST`, after the `start` branch, add:
```python
        elif body.get("action") == "replay":
            from council_server.record import replay_events
            import os, threading, time
            path = body.get("path") or os.path.join(ROOT, "runs", "golden.jsonl")
            def play():
                for evt in replay_events(path, speed=float(body.get("speed", 1.0))):
                    self.hub.publish(evt)
            threading.Thread(target=play, daemon=True).start()
```

- [ ] **Step 3: gitignore run logs except the golden one**

Append to `branchscape/.gitignore`:
```
runs/*.jsonl
!runs/golden.jsonl
```
Create `branchscape/runs/.gitkeep` (empty) so the dir exists.

- [ ] **Step 4: Verify the suite still passes**

Run: `cd branchscape && python3 -m unittest discover -s council_server -p "*_test.py"`
Expected: all PASS (no test depends on the runner factory; this is wiring).

- [ ] **Step 5: Commit**

```bash
git add council_server/__main__.py council_server/app.py runs/.gitkeep .gitignore
git commit -m "feat(council-live): orchestrator runner + per-run recording + replay route"
```

---

## Task 11: Browser — render the full deliberation (tool chips, votes, verdict)

Extend `live.js` rendering + `ui.js` so the full event stream shows: tool chips when agents query, votes lighting up reaction badges, and the verdict.

**Files:**
- Modify: `branchscape/council/live.js` (extend `render`; reducer already handles votes/verdict)
- Modify: `branchscape/council/ui.js` (add `showToolChip`, reuse `setReactions`/`setConfidence`)
- Modify: `branchscape/council/live.test.js` (add reducer coverage for tool_result + verdict)

- [ ] **Step 1: Add failing reducer tests**

Append to `council/live.test.js` before `report();`:
```javascript
test('tool_call/tool_result tracked; verdict captured', () => {
  let s = initialState();
  s = applyEvent(s, { type: 'tool_call', agent: 'market', data: { name: 'query_data', input: { metric: 'branch_count' } } });
  assert.strictEqual(s.lastTool.name, 'query_data');
  s = applyEvent(s, { type: 'verdict', agent: 'chair', data: { text: 'We recommend X', votes: [] } });
  assert.strictEqual(s.verdict.text, 'We recommend X');
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd branchscape && node council/live.test.js`
Expected: FAIL — `s.lastTool` is undefined.

- [ ] **Step 3: Extend the reducer + render in live.js**

In `applyEvent`, add cases:
```javascript
      case 'tool_call': s.lastTool = { agent: evt.agent, name: evt.data.name, input: evt.data.input }; break;
      case 'tool_result': s.lastToolResult = { agent: evt.agent, name: evt.data.name, result: evt.data.result }; break;
```
Extend `render`:
```javascript
    if (evt.type === 'tool_call' && typeof CouncilUI.showToolChip === 'function')
      CouncilUI.showToolChip(evt.agent, evt.data.name + '(' + (evt.data.input.metric || '') + ')');
    if (evt.type === 'vote_cast') CouncilUI.setReactions(Object.fromEntries(
      state.votes.map(v => [v.agent || 'market', v.stance === 'oppose' ? 'object' : (v.stance === 'conditional' ? 'conditional' : 'agree')])));
    if (evt.type === 'verdict') { CouncilUI.setActiveSpeaker('chair', evt.data.text); CouncilUI.setPhase('VERDICT'); }
```
> Note: `vote_cast` events carry the agent in `evt.agent`; ensure the orchestrator's `cast_vote` emit includes `agent` (it does — AgentRunner emits with `"agent": self.id`). Store agent on each vote in the reducer:
```javascript
      case 'vote_cast': s.votes = s.votes.concat([Object.assign({ agent: evt.agent }, evt.data)]); break;
```
(Replace the existing `vote_cast` case from Task 5.)

- [ ] **Step 4: Add `showToolChip` to ui.js**

Add to the `CouncilUI` returned object (and define it) a minimal chip near the agent node:
```javascript
  function showToolChip(agentId, label) {
    const node = nodeEls[agentId]; if (!node) return;
    const chip = document.createElement('div');
    chip.className = 'c-toolchip';
    chip.textContent = '⚙ ' + label;
    chip.style.cssText = 'position:absolute;left:50%;top:-26px;transform:translateX(-50%);font-size:9px;white-space:nowrap;padding:2px 7px;border-radius:10px;background:rgba(20,40,66,.95);border:1px solid #2a5a8c;color:#9fd0ff';
    node.appendChild(chip);
    setTimeout(() => chip.remove(), 4000);
  }
```
Add `showToolChip` to the `return { ... }` list.

- [ ] **Step 5: Run reducer tests**

Run: `cd branchscape && node council/live.test.js`
Expected: `pass=3 fail=0`.

- [ ] **Step 6: Commit**

```bash
git add council/live.js council/ui.js council/live.test.js
git commit -m "feat(council-live): render tool chips, votes, and verdict from the live stream"
```

---

## Task 12: Full live verification + golden run + README

**Files:**
- Create: `branchscape/runs/golden.jsonl` (captured real run — committed for the public/replay build)
- Modify: `branchscape/README.md` (Phase-2 live section)

- [ ] **Step 1: Full FAKE run end-to-end (no key) — proves the whole pipe**

```bash
cd branchscape && COUNCIL_FAKE=1 python3 -m council_server 8078
```
Open `http://localhost:8078/council.html?live`, hard-refresh, console: `__council.start('Open one new branch in Maricopa — balance deposit growth with community access')`.
**Identity gate:** `document.title === 'THE COUNCIL — BRANCHSCAPE Act 2'`.
**Expected:** phases advance mandate→gather→positions→crossExam→vote; agent nodes light up in turn; the run completes with a verdict in the caption. (Text is "fake" placeholder — we're checking the *flow*, not content.) Screenshot.

- [ ] **Step 2: Full REAL run (needs key) — the actual deliverable**

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # user provides
cd branchscape && python3 -m council_server 8078
```
Same open + start. **Expected (the real evidence):** genuinely-generated agent reasoning streams in; at least one **tool_call chip** appears (an agent querying data); agents reference each other in crossExam; votes light up reaction badges; the Chair delivers an emergent verdict. Run it **twice** — the two runs should differ (proof it's not scripted). Capture a screenshot of a mid-deliberation moment and the verdict. **This is the required proof before declaring P2b done; prefer a user hard-refresh for the authoritative check.**

- [ ] **Step 3: Save the golden run**

After a good real run, copy its log:
```bash
cd branchscape && cp "$(ls -t runs/run-*.jsonl | head -1)" runs/golden.jsonl
```

- [ ] **Step 4: Verify replay (offline-safe fallback)**

```bash
cd branchscape && python3 -m council_server 8078   # any mode; replay reads the file
```
Open `http://localhost:8078/council.html?live`, console: `fetch('/control',{method:'POST',body:JSON.stringify({action:'replay'})})`.
**Expected:** the saved real run replays through the same renderer with original-ish pacing — indistinguishable from live. This is the stage fallback.

- [ ] **Step 5: README section**

Append to `branchscape/README.md`:
```markdown
## THE COUNCIL: Live (Phase 2) — real multi-agent

Six real Claude agents deliberate live over the Maricopa data and emerge a branch-siting
recommendation. A local Python server holds your API key and streams the deliberation to
the browser.

- **Run live:** `export ANTHROPIC_API_KEY=sk-...` then `python3 -m council_server 8078`,
  open `http://localhost:8078/council.html?live`, and `__council.start("<your mandate>")`
  in the console (presenter UI lands in P2d).
- **No-key dry run:** `COUNCIL_FAKE=1 python3 -m council_server 8078` (flow only, canned text).
- **Replay the golden run (offline-safe stage fallback):** start the server and POST
  `{"action":"replay"}` to `/control` — replays `runs/golden.jsonl` through the same UI.
- **Tests:** `python3 -m unittest discover -s council_server -p "*_test.py"` (mocked Claude,
  no key needed) and `./run-tests.sh` for the JS reducer.
- **Fallback ladder:** live agents → recorded golden-run replay → Phase-1 deterministic
  `demo` mode (the original `council.html` path). The public GitHub Pages build is replay-only.
- Phase 2c (live web search + agents drawing on the map) and 2d (presenter controls + polish)
  are separate later additions.
```

- [ ] **Step 6: Commit**

```bash
git add runs/golden.jsonl README.md
git commit -m "feat(council-live): golden recorded run + README; P2b complete (real-run verified)"
```

---

## Self-Review (completed against the spec)

- **Spec §5 architecture** (server orchestrator + agent runners + tool layer + recorder/replayer + SSE/control) → Tasks 1-10. ✔
- **Spec §6 agents** (6 real Claude conversations, role prompts, shared transcript, Devil attacks, Chair synthesizes) → Tasks 7, 9. ✔
- **Spec §7 tools** → `query_data` + `cast_vote` in Task 6; `web_search` + `map_action` are explicitly **P2c (out of this plan)**. ✔ (documented deferral)
- **Spec §8 five beats facilitated** → Task 9 orchestrator (`mandate/gather/positions/crossExam/vote`). ✔
- **Spec §9 presenter controls** → `start` + `call_question` route stub in Task 4; `interject`/mode-toggle are **P2d (out of this plan)**. ✔ (documented deferral)
- **Spec §10 reliability** → Recorder/Replayer (Task 8), replay route + golden run (Tasks 10, 12); deterministic `demo` mode preserved (the non-`?live` boot path, Task 5). ✔
- **Spec §11 files** → `council_server/` package + `council/live.js`, `ui.js` extension, `council.html` `?live`. ✔
- **Spec §12 phasing** → this plan = P2a (Tasks 1-5) + P2b (Tasks 6-12); P2c/P2d are separate plans. ✔
- **Spec §13 testing** → Python `unittest` with FakeClaude (no key in CI); JS reducer via node harness; identity-gated manual browser checks; real-run-required-before-"verified". ✔
- **Type/name consistency:** event types, agent ids, beat ids, tool names, routes, `CouncilLive` global, `stream_agent_turn` signature, and the `emit(event_dict)` contract are identical across Tasks 2-11. ✔
- **Placeholder scan:** every code step has complete code; no TBD/TODO. Model id `claude-sonnet-4-5` is the one value flagged to confirm at live-verification (tests never use it). ✔

## Out of scope (separate later plans)
- **P2c:** `web_search` (cache-first + rehearsal cache) and `map_action` (agents drop pins / draw overlays as they reason).
- **P2d:** presenter `interject` mid-run, `call_question` UI button, streaming-thought visual polish, `mode` toggle (live/replay/demo) in the UI, and recording the canonical golden run for the public GitHub Pages (replay-only) build.
