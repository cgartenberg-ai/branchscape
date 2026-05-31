# branchscape/council_server/agents.py
import json
from council_server import tools

AGENT_IDS = ["chair", "market", "risk", "community", "realestate", "devil"]

ROLE_PROMPTS = {
    "market": "You are the MARKET ANALYST on a community bank's branch-siting council for "
        "Maricopa County, AZ. You care about deposit-growth opportunity: household income, "
        "demand, and where deposits are under-captured. Use query_data to ground every claim "
        "in real numbers. Be concise (2-3 sentences), cite figures, and engage other members' points.",
    "risk": "You are the RISK OFFICER on a Maricopa County bank branch-siting council. You care "
        "about competition and saturation — too many nearby branches means cannibalization. Use "
        "query_data. Push back when others are over-optimistic. 2-3 sentences, cite figures.",
    "community": "You are the COMMUNITY / CRA OFFICER on a Maricopa County bank branch-siting "
        "council. You champion underbanked, lower-income tracts and CRA credit. Use query_data "
        "(underserved_tracts). Argue for mission, not just margin. 2-3 sentences, cite figures.",
    "realestate": "You are the REAL-ESTATE SCOUT on a Maricopa County bank branch-siting council. "
        "You weigh site cost and feasibility — higher-income areas cost more to enter. Use "
        "query_data. 2-3 sentences, cite figures.",
    "devil": "You are the DEVIL'S ADVOCATE on a Maricopa County bank branch-siting council. Your "
        "job is to ATTACK the current front-runner with real evidence — find its weakest "
        "dimension via query_data and force the council to price it in. Be sharp but fair. 2-3 sentences.",
    "chair": "You are the CHAIR of a Maricopa County bank branch-siting council. You synthesize "
        "the council's discussion into a single recommendation, preserving any dissent. When asked "
        "to call the vote, state the recommended tract and the confidence, and name the key caveat. "
        "3-4 sentences.",
}

# Default model per agent; specialists may use a faster tier in P2d. None -> client default.
MODEL_FOR = {}

class AgentRunner:
    """Runs one agent's turn: stream thinking, resolve tool calls, return final message."""
    def __init__(self, agent_id, dataset, client, emit, model=None):
        self.id = agent_id
        self.ds = dataset
        self.client = client
        self.emit = emit
        self.model = model or MODEL_FOR.get(agent_id)

    def run_turn(self, transcript, max_tool_rounds=3):
        system = ROLE_PROMPTS[self.id]
        messages = list(transcript)
        text, votes = "", []
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
                return {"text": text, "votes": votes}
            # append assistant tool_use, resolve each tool, append user tool_result, loop
            assistant_content = ([{"type": "text", "text": text}] if text else []) + [
                {"type": "tool_use", "id": tc["id"], "name": tc["name"], "input": tc["input"]}
                for tc in tool_calls]
            messages.append({"role": "assistant", "content": assistant_content})
            results = []
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
                                "content": json.dumps(out)})
            messages.append({"role": "user", "content": results})
            if votes:
                # a vote is a terminal action for the turn; emit any trailing text as the message
                if text:
                    self.emit({"type": "agent_message", "agent": self.id, "data": {"text": text}})
                return {"text": text, "votes": votes}
        self.emit({"type": "agent_message", "agent": self.id, "data": {"text": text}})
        return {"text": text, "votes": votes}
