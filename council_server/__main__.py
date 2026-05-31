# branchscape/council_server/__main__.py
import os, sys
from council_server.app import serve
from council_server.llm import ClaudeClient
from council_server.fake_llm import FakeClaude

def make_runner(hub, dataset):
    # P2a: one real agent turn streamed to the hub. Replaced by the orchestrator in P2b.
    use_fake = os.environ.get("COUNCIL_FAKE") == "1"
    def runner(mandate):
        client = (FakeClaude(scripted=[{"text": "Streaming a real thought about Maricopa branch siting.", "tool_calls": []}])
                  if use_fake else ClaudeClient())
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
