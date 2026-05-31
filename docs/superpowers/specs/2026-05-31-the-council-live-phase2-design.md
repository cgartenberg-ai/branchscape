# THE COUNCIL: Live — Phase 2 Design Spec

*Replace the deterministic brain with a genuine multi-agent system: real Claude agents that reason, dig for data, argue, and converge on a decision nobody scripted — on the existing "council of light" stage.*

- **Date:** 2026-05-31
- **Status:** Approved design → ready for implementation plan
- **Branch:** `design/the-council` (Phase 1 deterministic version is committed & 5/5 verified; it becomes the fallback floor)
- **Repo:** `branchscape/` (self-contained, movable, GitHub Pages–deployed)
- **Supersedes the BRAIN of:** `2026-05-31-the-council-design.md` (Phase 1). Reuses that spec's scenario, agent roster, visual language, and staging.

---

## 1. Why this exists (the pivot)

Phase 1 shipped a working, beautiful demo whose **brain is a deterministic scoring function and whose agents read pre-written lines**. It *looks* like deliberation but isn't one: agents don't read each other, don't change their minds for real, don't go find anything new. A banking audience that has seen genuine multi-agent systems (e.g. AI Village) will spot the difference instantly.

**Phase 2 makes the deliberation real.** Six Claude agents, each with a role and tools, genuinely reason over real data, search for outside evidence, respond to each other, argue, and emerge a recommendation — live, on stage, with the audience able to pose the question and interject mid-deliberation. The Phase 1 "council of light" UI, deck.gl Maricopa map, and 5-beat staging are **reused as the stage**; only the brain is replaced.

### The core reframe (drives every decision below)
**"Real" and "live" are different axes.** *Real* = the dialogue/reasoning/digging is genuinely agent-produced, not scripted (mandatory). *Live* = it happens in the room right now (a risk dial, not a realness dial). We are **always real**, **live by default**, with a **genuine pre-recorded run as the instant fallback** — because the audience can tell scripted from genuine, but cannot tell (from their seats) whether a genuine run happened now or an hour ago.

---

## 2. Locked decisions (from brainstorm 2026-05-31)

| Decision | Choice |
|---|---|
| Realness | Always real (no scripts in the main path) |
| Liveness posture | **Live by default + real dress-rehearsal run as instant fallback** |
| API access | User has an **Anthropic API key**; a local server holds it (never the browser) |
| Data reach | Loaded FDIC/HMDA/CRA/income **+ live web search**, cached during rehearsal |
| Orchestration | **A — Facilitated / Chair-driven** (orchestrator runs beats; agents reason freely within them; a real Chair calls the vote) |
| Pacing | **Presenter-controlled** with a tight default path + a "call the question" control |
| Stage | Reuse council-of-light UI + deck.gl map + 5-beat staging |
| Fallback floor | Phase 1 deterministic engine remains as an optional zero-dependency "demo mode" |

---

## 3. Goals & Non-Goals

**Goals**
- Genuine emergent multi-agent deliberation: real reasoning, real tool use, real disagreement, real convergence.
- Visible "work": stream each agent's thinking; show tool calls and their results; draw findings onto the map as agents query.
- Presenter can pose the question and **inject** mid-deliberation; agents actually respond.
- Bulletproof on stage: live by default, but never a blank screen (recorded-real replay → deterministic demo-mode floor).
- Reuse the Phase 1 stage; keep the folder self-contained and movable.

**Non-Goals (YAGNI)**
- Not fully autonomous AI-Village-style free-for-all (rejected: timing/wander/deadlock risk on a one-shot stage). Facilitated, not chaotic.
- No multi-model (GPT/Gemini) agents — all Claude.
- No audience-phone participation (presenter-driven, as in Phase 1).
- No persistent cross-session agent memory (each run is fresh; the only "memory" is the shared transcript of the current run).
- Not a production lending/credit tool — an educational showcase.

---

## 4. Success Criteria
- A full deliberation runs live from a typed mandate to a Chair-synthesized verdict, with **visibly streamed agent reasoning** and **at least one genuine position change** during cross-examination.
- Agents make **real tool calls** (data + web) whose results are visible and influence the argument.
- The presenter can **inject** a steer mid-run and see agents incorporate it on the next turn.
- If the server/stream/API is unavailable, the browser **replays a real recorded run** through the same renderer with no visible downgrade; `?offline` runs entirely from cache/recording.
- Two runs of the same mandate are **recognizably different** (proof it's not scripted), yet both coherent.

---

## 5. System Architecture

Two processes: a **stage laptop server** (holds the key, runs the agents) and the **browser** (the stage). They speak over a one-way event stream (server→browser) plus a small control channel (browser→server).

```
Browser (council.html)
  ▲  event stream: phase_change / agent_thinking / agent_message /
  │                tool_call / tool_result / map_action / vote_cast / verdict / error
  │  control:      POST start{mandate} · POST interject{text} · POST call_question · POST mode
  ▼
council_server.py   (ANTHROPIC_API_KEY in env only)
  ├─ Orchestrator      — runs the 5 beats; owns shared transcript + turn order; emits events
  ├─ AgentRunner[6]    — one Claude Messages API stream per agent; resolves tool calls
  ├─ ToolLayer         — query_data, web_search(cached), map_action, cast_vote
  ├─ Recorder          — appends every emitted event to a run log (JSONL)
  └─ Replayer          — streams a saved "golden" run log to the browser as if live
```

**Transport:** Server-Sent Events (SSE) for the server→browser stream (simple, unidirectional, auto-reconnect, no extra deps); plain `POST` for control. (WebSocket is an acceptable alternative if bidirectional turns out cleaner; SSE is the default for simplicity.)

**Why a custom thin server over the full Agent SDK:** we need fine control over turn-taking, parallel phases, token streaming to a *custom* browser UI, and a recorder/replayer. A direct Messages API integration (streaming + tool use) is the most transparent path. The `claude-api` skill informs the implementation (prompt caching of the big role/system prompts + shared context is expected).

---

## 6. The Agents

Same 6-role roster as Phase 1 (Chair, Market Analyst, Risk Officer, Community/CRA Officer, Real-Estate Scout, Devil's Advocate), now each a **real Claude conversation** with:
- a **role system prompt**: expertise, what it advocates for, its personality, the tools it may call, and explicit instructions to (a) cite evidence from tools, (b) engage other agents' specific points, (c) be willing to change position when the evidence warrants;
- access to the **shared transcript** (all prior messages this run) each turn;
- the **tool set** in §7.

**Chair** is a real agent: given the transcript, it decides phase transitions and synthesizes the final recommendation (preserving dissent). **Devil's Advocate** is prompted to genuinely attack the current front-runner using real evidence (data or a web finding), not a canned objection.

Role prompts live in `council/agents.js` (shared with the browser for display) plus a server-side prompt module with the full instructions. Personalities are tuned in rehearsal.

---

## 7. Tools (server-side, exposed to agents via the Messages API tool-use interface)

| Tool | Signature | Backing | Notes |
|---|---|---|---|
| `query_data` | `(metric, area?)` → rows/summary | the loaded `BRANCH_DATA`, `HMDA`, `CRA*`, `INCOME`, `TRACTS` JSON | metrics: deposits, deposit-gap, branch saturation, mortgage lending, small-biz lending, income. Returns compact, citeable numbers. |
| `web_search` | `(query)` → results | real search provider, **cache-first** | rehearsal populates a `query→result` cache (JSON on disk); showtime uses cache first with a short timeout; `?offline` = cache only. |
| `map_action` | `(kind, payload)` | emitted as a `map_action` stream event | kinds: drop_pin(lon,lat,label), overlay(signal), highlight_zone(geoid), clear. Lets agents *draw their reasoning* on the map. |
| `cast_vote` | `(zone, stance, rationale)` | recorder + verdict tally | stance ∈ {support, conditional, oppose}. |

All tool calls and results are emitted as stream events so the UI shows the work. Tool execution is bounded by a per-call timeout.

---

## 8. The 5 Beats (now real work, facilitated by the orchestrator)

1. **Mandate.** Presenter types the question; orchestrator seeds the shared transcript and emits `phase_change`.
2. **Gather.** All specialist agents run **in parallel**; each calls `query_data` / `web_search` and may `map_action` to draw findings. Tool chips + overlays stream live. (Parallelism keeps wall-clock down despite real calls.)
3. **Positions.** Each agent posts an opening stance *with cited evidence*; candidate pins appear. (Can be parallel — independent statements.)
4. **Cross-examination.** Sequential/interleaved: the orchestrator feeds each agent the others' messages; agents respond, the Devil attacks, positions shift. **Presenter inject** adds a message to the transcript that all agents see on their next turn.
5. **Vote.** Chair calls the question (or presenter forces via `call_question`); each agent `cast_vote`s with rationale; Chair synthesizes the recommendation; dissent preserved on the decision card.

The orchestrator enforces beat boundaries and turn order; **content within each beat is emergent.**

---

## 9. Presenter Controls (live)
- **Start** with a typed mandate (the audience's real question).
- **Inject** free text at any time → enters the shared transcript for the next turn.
- **Call the question** → force the vote beat immediately.
- **Mode** toggle: `live` (real agents) · `replay` (golden run) · `demo` (Phase 1 deterministic floor).
- Keyboard parity with Phase 1 where it still makes sense (space = let-it-run/pause the cadence between turns).

---

## 10. Reliability & Venue Safety (the net under the trapeze)
- **Per-turn timeout:** a stalled agent is skipped; the Chair notes the absence and continues.
- **Web search cache-first:** rehearsal fills the cache; showtime prefers cache with a short live timeout; `?offline` is cache-only.
- **Recorded-real fallback:** every run is logged as JSONL. Dress-rehearse before the talk, pick the best **real** run as the "golden" log. If wifi/API/stream fails at showtime, the browser switches to **replay** of the golden log through the *same* renderer — indistinguishable, and genuinely real (just earlier).
- **Deterministic floor:** Phase 1's engine + script remain as `demo` mode — a zero-network, zero-key path that always produces a coherent show. So there is never a blank screen.
- **Key safety:** the API key lives only in the server's environment. The public GitHub Pages build is **replay-only** (ships a golden log, no key, no server).
- **No-CDN / offline:** inherited from Phase 1 (vendored libs, `?offline`).

---

## 11. Module / File Plan (inside `branchscape/`)

**New**
- `council_server.py` — orchestrator + agent runners + tool layer + recorder/replayer + SSE/control endpoints. (Python to match the existing stack; may be split into `council_server/` package: `orchestrator.py`, `agents.py`, `tools.py`, `record.py`, `app.py`.)
- `council/live.js` — browser stream client: subscribes to SSE, dispatches events to the UI; presenter controls (start/inject/call-question/mode).
- `council/prompts/` (or server-side) — the full role system prompts.
- `runs/` — recorded run logs (JSONL); the chosen golden log is referenced by the replay path. (gitignored except a curated golden log for the public build.)
- `web_cache.json` — rehearsal web-search cache.

**Reused / extended**
- `council/ui.js` — extended to render **streaming thoughts** (token deltas into the caption) and **tool chips**; everything else (nodes, spotlight, meter, beams, map chips) stays.
- `council/map.js` — add handlers for `map_action` events (pins/overlays/highlight) driven by agents.
- `council/agents.js` — gains display metadata for richer role cards; full prompts live server-side.
- `council.html` — load `council/live.js`; keep the existing shell and `?offline`.

**Demoted to fallback (`demo` mode)**
- `council/engine.js`, `council/script.js`, `council/director.js` — the Phase 1 deterministic path, selectable as the ultra-floor.

---

## 12. Phasing (Phase 2 is itself sizable — build in shippable slices)

- **P2a — Prove the pipe.** `council_server.py` streams ONE agent's live Claude tokens to the browser caption over SSE. Confirms key, streaming, transport, rendering.
- **P2b — Facilitated 6-agent deliberation over loaded data** (no web yet): orchestrator + role prompts + `query_data` + `cast_vote` + Chair synthesis; Recorder + Replayer; `?offline` plays a golden log. **This alone is the core wow.**
- **P2c — Live web search + map actions:** `web_search` with rehearsal cache; `map_action` so findings draw on the map live.
- **P2d — Live interaction + polish:** presenter inject + call-the-question; streaming-thought visual polish; mode toggle (live/replay/demo); record the golden run for the public build.

Each slice is independently demoable. If time is short, **P2b is the heart**; P2a+P2b deliver genuine emergent deliberation; P2c/P2d add digging + interactivity + polish.

---

## 13. Testing & Verification
- **Logic (Node, existing harness):** tool implementations (`query_data` over real JSON), vote tallying, transcript assembly, replay-log parsing — unit-tested with `council/_harness.js` (`run-tests.sh`).
- **Server:** a smoke test that the orchestrator runs a full beat sequence against a **mocked** Claude (canned tool/use responses) — deterministic, no key needed in CI.
- **Live (identity-gated browser):** one real run end-to-end on `council.html` (assert `document.title` first), watching streamed thoughts, a real tool call, a position change, and a verdict. **A real run is required evidence before claiming "works"** (per the hard lessons of the Phase 1 build — no "verified" without machine-read proof on the correct page).
- **Fallback:** verify `?offline`/replay produces the full show from a golden log with no network.

---

## 14. Risks & Mitigations
| Risk | Mitigation |
|---|---|
| Latency (real calls take real time) | Parallelize independent beats; **stream thinking so the wait IS the show**; presenter can call the question. |
| Wifi/API failure on stage | Recorded-real replay → deterministic demo floor; cache-first web search. |
| Agent says something naive/wrong to bankers | Low-stakes optimistic domain (branch siting); grounded tools (cite data); Devil's Advocate surfaces weak logic; presenter in the loop. |
| Agents converge instantly (no drama) | Role prompts tuned for genuine advocacy + a Devil prompted to attack; rehearse mandates that create real tension (profit vs. mission). |
| Key leakage | Key server-side only; public build is replay-only. |
| Cost | Negligible (cents–low dollars per run); not a constraint. |
| Non-determinism breaks rehearsal | Rehearse the *system*, not the output; the golden log captures one great real run for guaranteed replay. |

---

## 15. Open Questions (resolve during P2a/P2b)
- Exact web-search provider/tool (Anthropic web search tool vs. a search API) — pick the simplest that caches cleanly.
- SSE vs. WebSocket — default SSE; revisit if presenter-inject needs tighter bidirectional timing.
- Per-agent model tier (e.g. a faster model for specialists, a stronger one for the Chair/Devil) — tune for latency vs. quality in rehearsal.
- How "tight default path" expresses with live agents (a recommended mandate + rehearsed cadence) vs. fully open.

---

## 16. Out of Scope
- Multi-model agents; audience-phone interaction; persistent agent memory; analog metros (that's the separate Phase 3); production credit decisioning.
