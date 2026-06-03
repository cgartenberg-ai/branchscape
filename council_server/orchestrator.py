# branchscape/council_server/orchestrator.py
import collections, queue
from council_server.agents import AgentRunner, build_profile_preamble

SPECIALISTS = ["market", "risk", "community", "realestate", "devil"]

class Orchestrator:
    """Facilitated, Chair-driven 5-beat deliberation. Content within beats is emergent.

    Robustness contract (fixes the live-run "stall"): the run ALWAYS concludes with a
    VISIBLE verdict and a run_end. Concretely:
      * every agent turn is wrapped so a failure becomes a recorded `error` event and
        the deliberation continues (one bad turn can't freeze the show);
      * the Chair's synthesis turn is TOOL-FREE, so it produces prose instead of
        spending the turn on query_data and returning empty text (the actual cause of
        the user's blank ending);
      * the verdict carries a deterministic vote `tally`, and if the Chair's text is
        still empty we derive a non-empty summary from the votes — so the conclusion
        is never invisible;
      * run() is wrapped in try/finally so verdict + run_end fire no matter what.
    """
    def __init__(self, dataset, client, emit):
        self.ds = dataset
        self.client = client
        self.emit = emit
        self.transcript = []   # shared chat all agents see
        self.votes = []
        self.profile_preamble = ""  # set per-run from the presenter's bank profile
        self._inbox = queue.Queue()  # presenter "[THE ROOM]" messages awaiting fold-in

    def _runner(self, agent_id):
        return AgentRunner(agent_id, self.ds, self.client, emit=self.emit,
                           profile_preamble=self.profile_preamble)

    def inject(self, text):
        """Thread-safe (called from the HTTP handler thread): queue a presenter/room
        message to be folded into the live deliberation at the next turn boundary."""
        self._inbox.put(text)

    def _drain_injections(self):
        """Fold every pending room message into the shared transcript as a directive the
        remaining agents (and the Chair) must take seriously, and surface each as a visible
        `room_inject` event so the HUD shows the redirect entering the debate."""
        while True:
            try:
                text = self._inbox.get_nowait()
            except queue.Empty:
                break
            self.transcript.append({"role": "user",
                "content": f"[THE ROOM — a directive from the audience that you MUST take "
                           f"seriously and respond to] {text}"})
            self.emit({"type": "room_inject", "data": {"text": text}})

    def _say(self, agent_id, instruction, tools_enabled=True):
        """Resilient single turn: a failure becomes a recorded error + empty result,
        so one bad turn can never abort the whole deliberation."""
        self._drain_injections()  # fold any pending presenter "[THE ROOM]" input in first
        msgs = self.transcript + [{"role": "user", "content": instruction}]
        try:
            result = self._runner(agent_id).run_turn(msgs, tools_enabled=tools_enabled)
        except Exception as e:  # network / stream / SDK failure on this turn
            self.emit({"type": "error", "agent": agent_id,
                       "data": {"message": f"{agent_id} turn failed: {e}"}})
            return {"text": "", "votes": []}
        if result.get("text"):
            self.transcript.append({"role": "user", "content": f"[{agent_id}] {result['text']}"})
        self.votes.extend(result.get("votes", []))
        return result

    def _phase(self, beat):
        self.emit({"type": "phase_change", "data": {"beat": beat}})

    def _tally(self):
        return dict(collections.Counter(v.get("stance", "support") for v in self.votes))

    def _recommended_zone(self):
        zones = collections.Counter(v.get("zone") for v in self.votes if v.get("zone"))
        return zones.most_common(1)[0][0] if zones else None

    def _fallback_summary(self):
        tally = self._tally()
        parts = ", ".join(f"{n} {stance}" for stance, n in tally.items()) or "no votes cast"
        zone = self._recommended_zone()
        where = f"tract {str(zone)[-4:]}" if zone else "no clear front-runner"
        return f"The council has voted ({parts}). Recommendation: {where}."

    def run(self, mandate, profile=None):
        self.profile_preamble = build_profile_preamble(profile)
        self.emit({"type": "run_start", "data": {"mandate": mandate, "profile": profile}})
        chair_text = ""
        try:
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
            for a in SPECIALISTS:
                self._say(a, f"{a}: you MUST call the cast_vote tool now with your final "
                             f"zone, stance, and rationale.")
            # Chair synthesizes from the transcript — NO tools, so it produces prose,
            # not another round of queries that returns empty. The Chair's judgment is
            # final: it sees the tally + plurality and may OVERRULE it (acknowledging it).
            plurality = self._recommended_zone()
            plurality_str = f"tract {str(plurality)[-4:]}" if plurality else "no clear plurality"
            chair = self._say("chair",
                              f"chair: the votes are in. Tally by stance: {self._tally()}. "
                              f"The plurality of votes favors {plurality_str}. As Chair, your "
                              f"judgment is FINAL: you may endorse the plurality or OVERRULE it. "
                              f"If you overrule, explicitly acknowledge the plurality and explain "
                              f"why you decide otherwise. In 3-4 sentences, name the recommended "
                              f"tract, the confidence, and the key caveat/dissent. Do NOT call any "
                              f"tools — synthesize from the discussion above.",
                              tools_enabled=False)
            chair_text = (chair.get("text") or "").strip()
        finally:
            text = chair_text or self._fallback_summary()
            self.emit({"type": "verdict", "agent": "chair",
                       "data": {"text": text, "votes": self.votes, "tally": self._tally()}})
            self.emit({"type": "run_end", "data": {}})
