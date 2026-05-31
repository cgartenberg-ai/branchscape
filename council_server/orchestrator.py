# branchscape/council_server/orchestrator.py
from council_server.agents import AgentRunner

SPECIALISTS = ["market", "risk", "community", "realestate", "devil"]

class Orchestrator:
    """Facilitated, Chair-driven 5-beat deliberation. Content within beats is emergent."""
    def __init__(self, dataset, client, emit):
        self.ds = dataset
        self.client = client
        self.emit = emit
        self.transcript = []   # shared chat all agents see
        self.votes = []

    def _runner(self, agent_id):
        return AgentRunner(agent_id, self.ds, self.client, emit=self.emit)

    def _say(self, agent_id, instruction):
        msgs = self.transcript + [{"role": "user", "content": instruction}]
        result = self._runner(agent_id).run_turn(msgs)
        if result["text"]:
            self.transcript.append({"role": "user", "content": f"[{agent_id}] {result['text']}"})
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
            self._say(a, f"{a}: state your opening recommendation (a census tract) with cited evidence.")

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
