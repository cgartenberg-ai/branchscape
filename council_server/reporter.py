# branchscape/council_server/reporter.py
# Turns a finished deliberation (its event list) into two artifacts:
#   * <stem>-transcript.md — the full readable debate (deterministic, no LLM)
#   * <stem>-report.md     — an AI-synthesized decision memo (one Claude call)
import json, os

DISPLAY = {
    "chair": "Chair / President", "market": "Market Analyst", "risk": "Risk Officer",
    "community": "Community / CRA Officer", "realestate": "Real-Estate Scout",
    "devil": "Devil's Advocate",
}
BEAT_TITLE = {
    "mandate": "The Mandate", "gather": "Gathering Data", "positions": "Opening Positions",
    "crossExam": "Cross-Examination", "vote": "The Vote",
}

def _name(agent):
    return DISPLAY.get(agent, agent or "—")

def build_transcript(events, mandate=None):
    """Deterministic markdown of the whole debate — agent words, queries, votes, verdict."""
    m = mandate
    for e in events:
        if e.get("type") == "run_start":
            m = e.get("data", {}).get("mandate") or m
    out = ["# THE COUNCIL — Deliberation Transcript", ""]
    if m:
        out += [f"**Mandate:** {m}", ""]
    for e in events:
        t = e.get("type"); d = e.get("data", {}) or {}
        if t == "phase_change":
            out += ["", f"## {BEAT_TITLE.get(d.get('beat'), d.get('beat', '')).upper()}", ""]
        elif t == "agent_message" and (d.get("text") or "").strip():
            out += [f"**{_name(e.get('agent'))}:** {d['text'].strip()}", ""]
        elif t == "tool_call":
            out.append(f"- _{_name(e.get('agent'))} queried_ `{d.get('name')}({json.dumps(d.get('input', {}))})`")
        elif t == "vote_cast":
            out.append(f"- 🗳 **{_name(e.get('agent'))} votes {d.get('stance', '?')}** "
                       f"for tract {str(d.get('zone', '?'))[-4:]} — {d.get('rationale', '')}")
        elif t == "verdict":
            out += ["", "## VERDICT", "", (d.get("text") or "").strip()]
            if d.get("tally"):
                out += ["", f"_Vote tally: {json.dumps(d['tally'])}_"]
        elif t == "error":
            out.append(f"> ⚠ {d.get('message', 'error')}")
    return "\n".join(out).rstrip() + "\n"

SECRETARY_PROMPT = (
    "You are the secretary of a bank branch-siting council. Given the deliberation "
    "transcript below, write a concise DECISION MEMO in markdown with EXACTLY these "
    "sections:\n"
    "## Recommendation  (the recommended census tract + the council's confidence)\n"
    "## Key Arguments For\n"
    "## Key Arguments Against\n"
    "## Reasoning  (why the council reached this decision)\n"
    "## Dissent  (any minority view; say 'None recorded' if unanimous)\n"
    "## Potential Downsides & Risks\n"
    "Be specific and attribute points to the agents who made them. Do not invent facts "
    "beyond the transcript."
)

def build_report(transcript_md, client):
    """One LLM call (no tools) that synthesizes the decision memo from the transcript."""
    parts = []
    for kind, payload in client.stream_agent_turn(
            system=SECRETARY_PROMPT,
            messages=[{"role": "user", "content": transcript_md}],
            tools=[]):
        if kind == "final":
            parts.append(payload["text"])
    return (parts[0] if parts else "").strip() + "\n"

def write_artifacts(events, runs_dir, stem, client):
    """Write <stem>-transcript.md and <stem>-report.md into runs_dir.
    Returns {'transcript': url, 'report': url} for the browser to link."""
    os.makedirs(runs_dir, exist_ok=True)
    transcript = build_transcript(events)
    with open(os.path.join(runs_dir, f"{stem}-transcript.md"), "w", encoding="utf-8") as f:
        f.write(transcript)
    report = build_report(transcript, client)
    with open(os.path.join(runs_dir, f"{stem}-report.md"), "w", encoding="utf-8") as f:
        f.write(report)
    return {"transcript": f"/runs/{stem}-transcript.md", "report": f"/runs/{stem}-report.md"}
