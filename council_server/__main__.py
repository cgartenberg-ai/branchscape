# branchscape/council_server/__main__.py
import os, sys, time
from council_server.app import serve
from council_server.llm import ClaudeClient
from council_server.fake_llm import FakeClaude
from council_server.orchestrator import Orchestrator
from council_server.record import Recorder
from council_server import envfile

RUNS_DIR = os.path.join(os.path.dirname(__file__), "..", "runs")
ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")

def _build_fake_client():
    """Enough canned turns for a full keyless run: 5 gather + 5 positions +
    3 crossExam + 5 votes + 1 chair verdict. Votes carry a cast_vote tool call."""
    scripted = []
    for _ in range(5): scripted.append({"text": "Gathering data.", "tool_calls": []})
    for _ in range(5): scripted.append({"text": "My opening position is tract 12345.", "tool_calls": []})
    for _ in range(3): scripted.append({"text": "On reflection, I push back.", "tool_calls": []})
    for _ in range(5): scripted.append({"text": "Casting my vote.", "tool_calls": [
        {"id": "v", "name": "cast_vote",
         "input": {"zone": "04013012345", "stance": "support", "rationale": "widest gap"}}]})
    scripted.append({"text": "The council recommends tract 12345 at moderate confidence.", "tool_calls": []})
    return FakeClaude(scripted=scripted)

def make_runner(hub, dataset):
    """A full 6-agent orchestrated deliberation, streamed to the hub and recorded."""
    use_fake = os.environ.get("COUNCIL_FAKE") == "1"
    def runner(mandate):
        os.makedirs(RUNS_DIR, exist_ok=True)
        rec = Recorder(os.path.join(RUNS_DIR, f"run-{int(time.time())}.jsonl"))
        def emit(evt):
            rec.write(hub.publish(evt))  # hub stamps ts + defaults; recorder persists that same dict
        client = _build_fake_client() if use_fake else ClaudeClient()
        try:
            Orchestrator(dataset, client, emit).run(mandate)
        except Exception as e:
            hub.publish({"type": "error", "data": {"message": str(e)}})
        finally:
            rec.close()
    return runner

def _check_key():
    if os.environ.get("COUNCIL_FAKE") == "1":
        print("COUNCIL_FAKE=1 → using the canned fake agents (no API key needed).")
        return
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n  ⚠  ANTHROPIC_API_KEY is not set.\n"
              "     Real agents need it. Either:\n"
              "       put it in branchscape/.env  (ANTHROPIC_API_KEY=sk-ant-...), OR\n"
              "       export ANTHROPIC_API_KEY=sk-ant-...   then re-run, OR\n"
              "       COUNCIL_FAKE=1 python3 -m council_server <port>   (canned dry run)\n")
        sys.exit(1)
    print("ANTHROPIC_API_KEY detected → real agents enabled.")

if __name__ == "__main__":
    # .env autoload is a side effect, so it belongs here — NOT at module import time
    # (importing the package must stay clean so `unittest discover` works).
    envfile.load_env(ENV_PATH)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
    _check_key()
    print(f"Open  http://127.0.0.1:{port}/council.html?live   (use 127.0.0.1, NOT localhost)")
    serve(port, make_runner)
