# Session Handoff — THE COUNCIL: Live (real multi-agent demo)

**Date:** 2026-05-31 (long evening session)
**Project:** BRANCHSCAPE / THE COUNCIL — `/Users/cgart/Penn Dropbox/Claudine Gartenberg/Feedforward/playground/orgscience/branchscape`
**Session Focus:** Pivoted THE COUNCIL from a fake/deterministic demo to GENUINE multi-agent (real Claude agents that reason, query data, argue, vote). Built Phase 2a+2b, fixed a live-run "stall," added a transcript + AI decision-memo report feature.

---

## CRITICAL: Read This First

THE COUNCIL is **Act 2 of BRANCHSCAPE** — a stage demo for ~400 ABA bankers (~mid-June 2026). Six **real Claude agents** (Chair, Market Analyst, Risk Officer, Community/CRA Officer, Real-Estate Scout, Devil's Advocate) deliberate live over real Maricopa County banking data and emerge a branch-siting recommendation. A local Python server (`council_server/`) holds the API key and streams the deliberation to the browser over Server-Sent Events; the existing "council of light" deck.gl UI renders it. **The user LOVED the first real run** ("AMAZING, I LOVE IT") — the quality bar is set by that run (`runs/run-1780262035.jsonl`, full paragraphs with real figures).

Everything is committed and clean on branch `design/the-council` (NOT merged, NOT pushed). All tests pass: **29 Python server tests, 7 JS reducer tests, Phase-1 JS suite green.**

**Immediate next action:** The user APPROVED building the **bank-profile setup panel** (presenter UI: archetype presets + custom fields → agents reason AS that bank), but then said "stop and wait for instructions." So: **do NOT auto-start building. Confirm with the user first**, then build the setup panel as the next chunk.

---

## Where We Left Off

### Completed This Session
- [x] **Brainstormed + spec'd the Phase-2 pivot** to real multi-agent (`docs/superpowers/specs/2026-05-31-the-council-live-phase2-design.md`)
- [x] **Wrote the P2a+P2b implementation plan** (`docs/superpowers/plans/2026-05-31-the-council-live-phase2ab.md`, 12 tasks)
- [x] **Built P2a** (Tasks 1–5): data loader, SSE event hub, Claude client + FakeClaude test seam, HTTP app (SSE+control), browser live client. User confirmed real streaming works.
- [x] **Built P2b** (Tasks 6–12): query_data+cast_vote tools, role prompts + AgentRunner tool-use loop, recorder/replayer, 5-beat orchestrator, app wiring, browser render (tool chips/votes/verdict), README.
- [x] **`.env` support** for the API key (gitignored; auto-loaded; `.env.example` is the template)
- [x] **Fixed the live-run "stall"** (root-caused from the recorded run — see Implicit Knowledge)
- [x] **Built the report feature** (user's direct ask): per-run `transcript.md` + AI `report.md` decision memo, auto-written at run-end, with download links in the UI
- [x] **Diagnosed the "dumb/superficial debate" complaint** → it was a FAKE-mode/wrong-port run, not a regression (see Implicit Knowledge)

### In Progress / Not Started (Planned)
- [ ] **Bank-profile setup panel (NEXT, user-approved):** presenter panel on the `?live` page — archetype presets (Community / Rural / Commercial, 3 seeded realistic ABA archetypes) + custom fields (bank name, asset size, region, values, mandate) + "Convene the council" button. Must thread a `profile` object through `start{}` → orchestrator → agent `ROLE_PROMPTS` so agents reason AS that specific bank. This is the core of "P2d."
- [ ] **Bake the golden run** (`runs/golden.jsonl`) from a good REAL run for the offline replay fallback — needs a real-key run (Task 12 step 3, never completed; only fake runs were captured after the rich one).
- [ ] **P2c (separate later plan):** live `web_search` (cache-first) + `map_action` (agents draw pins/overlays on the map as they reason).
- [ ] **P2d remainder (separate later plan):** presenter `interject` mid-run, `call_question` button, mode toggle (live/replay/demo) in the UI, streaming-thought polish.
- [ ] **Phase 3 (separate):** analog metros (rerun fetchers for other counties) + place-name labels.

---

## Project Overview

### What This Project Is
BRANCHSCAPE is a cinematic deck.gl visualization of Maricopa County, AZ bank-branch "deposit topography" (glowing towers = FDIC deposits), built for a live talk to ~400 ABA member regional bankers to wow them with AI/Claude Code. THE COUNCIL is **Act 2**: on the same map, a team of AI agents makes a decision a human committee normally makes — *"where should we open the next branch?"* — gathering data, deliberating, arguing, and voting, live and transparently. Phase 1 was a deterministic engine + scripted lines (the user rejected it as a "canned decision tree"). Phase 2 (this session) makes the agents REAL.

### Key Files and Their Purpose
| File | Purpose |
|------|---------|
| `council.html` | The page shell. `?live` = real agents (Phase 2); plain = Phase-1 deterministic "demo." Loads vendored deck.gl/maplibre + data globals + all `council/*.js`. |
| `council_server/__main__.py` | Server entry. `make_runner` drives a full deliberation, records JSONL, writes transcript+report at run-end, emits `artifacts`. `.env` autoload + API-key check live here. Default port **8099**. |
| `council_server/orchestrator.py` | The 5-beat facilitated deliberation (mandate→gather→positions→crossExam→vote). Chair-driven. Guarantees a VISIBLE verdict + run_end (try/finally + per-turn error capture). |
| `council_server/agents.py` | `ROLE_PROMPTS` (the 6 agent personalities) + `AgentRunner.run_turn` (streams thinking, resolves tool calls; `tools_enabled` flag makes the Chair's synthesis turn tool-free). |
| `council_server/tools.py` | `query_data` (over real FDIC/CRA/income/tract data) + `cast_vote`. Skips Census 9800-9999 junk tracts. |
| `council_server/llm.py` | `ClaudeClient` — anthropic Messages API streaming + tool use. model=`claude-sonnet-4-5`, timeout=90s, max_tokens=1500. |
| `council_server/fake_llm.py` | `FakeClaude` — canned responses for KEYLESS tests. **The source of the "Gathering data." snippets — NOT used in real runs.** |
| `council_server/reporter.py` | `build_transcript(events)` (deterministic markdown) + `build_report(transcript, client)` (one Claude call → decision memo) + `write_artifacts`. |
| `council_server/{hub,record,envfile,data}.py` | SSE event hub (pub/sub), JSONL recorder/replayer, `.env` loader, data globals loader. |
| `council/live.js` | Browser SSE client. Pure `applyEvent` reducer + `verdictText()` (never-blank verdict) + `render()` into CouncilUI. Browser global `CouncilLive`. |
| `council/ui.js` | The "council of light" HUD (agent nodes, spotlight, caption, meter, tool chips, `showArtifacts` download panel). REUSED from Phase 1, extended. |
| `council/map.js` | deck.gl map (towers + overlays). REUSED from Phase 1. |
| `council/{agents,engine,director,script,map}.js` | Phase-1 deterministic "demo mode" (still the fallback floor). |

### Directory Structure
```
branchscape/
├── council.html                # page shell (?live = real, plain = demo)
├── council_server/             # Phase-2 Python server (real agents)
│   ├── __main__.py  app.py  orchestrator.py  agents.py  tools.py
│   ├── llm.py  fake_llm.py  reporter.py  hub.py  record.py  envfile.py  data.py
│   └── *_test.py               # stdlib unittest (mocked Claude, keyless)
├── council/                    # browser: live.js (P2) + Phase-1 ui/map/engine/director/script
│   ├── live.js  ui.js  map.js  *.test.js  _harness.js
├── data/*.js                   # window.BRANCH_DATA / TRACTS / CRA_TRACT / INCOME_DATA
├── runs/                       # JSONL run logs + generated .md (gitignored; golden.jsonl tracked)
├── .env                        # ANTHROPIC_API_KEY (gitignored)  /  .env.example (template)
├── run-tests.sh                # Phase-1 JS test gate (node segfault workaround)
└── docs/superpowers/{specs,plans}/  # design + implementation docs
```

### Key Concepts
1. **Two phases coexist:** `council.html?live` (real agents via server) vs `council.html` (Phase-1 deterministic demo). Fallback ladder: live → replay golden.jsonl → deterministic demo.
2. **SSE event protocol:** server publishes event dicts `{type, ts, agent, data}`; types: `run_start, phase_change, agent_thinking, agent_message, tool_call, tool_result, vote_cast, verdict, error, artifacts, run_end`. Browser reducer (`applyEvent`) is the single source of truth.
3. **Every run is recorded** to `runs/run-<ts>.jsonl` — this is the debugging goldmine (root-caused the stall from it).
4. **Real ≠ Live (design axis):** "real" = genuine agent reasoning (mandatory); "live" = happens now (risk dial). Stage plan: live-by-default + recorded-real golden replay fallback.

---

## Technical State

### Build/Run Status — ALL GREEN
```bash
cd "/Users/cgart/Penn Dropbox/Claudine Gartenberg/Feedforward/playground/orgscience/branchscape"
python3 -m unittest discover -s council_server -p "*_test.py"   # → Ran 29 tests OK
node council/live.test.js   # → RESULT tests=7 pass=7 fail=0 (see council/.last-test-result)
./run-tests.sh              # → ALL TESTS PASS (Phase-1 JS)
```

### Git Status
- Branch: `design/the-council` (NOT merged to main, NOT pushed)
- Working tree: **clean**
- HEAD: `6c56a3c feat(council-live): auto-write transcript+report at run-end + UI download links`

### Environment Requirements
- Python 3.13 (3.13.3); `anthropic` SDK 0.75 already installed; stdlib-only server (no Flask)
- `ANTHROPIC_API_KEY` — already in `branchscape/.env` (gitignored). Real mode is the DEFAULT (no env var needed).
- Node present but **segfaults on teardown (exit 139)** — JS tests gate on the `.last-test-result` file, never on exit code.

### How to run the REAL demo
```bash
pkill -f "http.server"; pkill -f council_server     # clear ALL strays first (critical — see gotcha)
cd "/Users/cgart/Penn Dropbox/Claudine Gartenberg/Feedforward/playground/orgscience/branchscape"
python3 -m council_server 8099
# open EXACTLY what it prints:  http://127.0.0.1:8099/council.html?live   (127.0.0.1, NOT localhost)
# hard-refresh (Cmd-Shift-R), then in browser console:
__council.start("Open one new branch in Maricopa — balance deposit growth with community access")
```

---

## Implicit Knowledge (CRITICAL — read before debugging anything)

1. **The "stall" was NOT a hang.** Root-caused from `runs/run-1780262035.jsonl`: the server completed in 3.6 min WITH a verdict+run_end, but the Chair spent its final turn making `query_data` tool calls and returned EMPTY text → `verdict.text==""` → browser rendered a BLANK ending (caption frozen on the Chair's pre-tool line). FIXED: Chair synthesis turn is now TOOL-FREE; verdict always carries a vote `tally`; empty chair text → derived summary; browser `verdictText()` never blanks; errors are surfaced. (Commits `175c200`, and browser-half folded into later commits.)

2. **The "superficial/dumb debate" was a WRONG-PORT / FAKE-mode run, NOT a regression.** Proof: the two most recent run logs contain the exact canned strings from `fake_llm.py` (`"Gathering data."`, `"My opening position is tract 12345."`). The user's browser hit **port 8078**, which was a leftover plain `python -m http.server 8078 --directory branchscape` (the Claude preview/dev tool's static server) — it has NO `/events` or `/control`, so the live stream silently failed and a cached fake run showed. The real rich run quality is intact in the code; the "2-3 sentences" prompt line was ALREADY present during the amazing run (model wrote paragraphs anyway), and max_tokens went UP. **Lesson: always kill strays and use the printed 127.0.0.1:8099 URL.**

3. **PORT GOTCHA (recurring, cost real time):** The Claude preview/dev tool repeatedly spawns its own `python -m http.server` on **port 8078** over IPv6. `localhost` resolves to IPv6 → hits the WRONG server (404 on /events, 501 on POST). ALWAYS use **127.0.0.1** (not localhost) and the **8099** default. Before any real run: `pkill -f "http.server"; pkill -f council_server`.

4. **Node segfaults on teardown (exit 139) on this machine** regardless of `--jitless`. Exit codes are MEANINGLESS for JS. The JS harness (`council/_harness.js`) writes a durable `council/.last-test-result` (gitignored) that `run-tests.sh` greps for `fail=0`. Python (the server) does NOT have this problem — its exit codes are reliable.

5. **`.env` autoload MUST stay inside the `__main__` guard, not at import time** — an import-time `.env` load once crashed `unittest discover`. (Learned the hard way; already fixed.)

6. **Data shape gotcha:** `BRANCH_DATA.branches` is (branch × 7 snapshot years) ≈ 4887 rows; each row's `dep` is an INT ($thousands) for that `year`, NOT a `{year: amount}` dict. `query_data` filters to the latest year → total_deposits=$171.9B, branch_count=675 (matches BRANCHSCAPE headline). Phase-1 `map.js` has a latent `dep['2024']` assumption that happens to render OK — noted, not fixed.

7. **Testing discipline that works here:** Python server logic = stdlib `unittest` with mocked `FakeClaude` (no key, no network). Browser logic = the pure `applyEvent` reducer via node harness. Real-agent behavior + live browser = ONLY verifiable by the USER (the preview tool keeps hijacking ports; the user's real browser is the reliable channel). NEVER claim "verified" without machine-read proof.

**User preferences discovered:**
- Loves genuine emergence over canned/scripted — rejected Phase 1 hard. Quality bar = the rich real run.
- Wants the demo to "absolutely floor" a banking audience; cares about gravitas + real data.
- Declined a LIVE/FAKE UI badge (chose "I'll always test on a throwaway port" instead — so: my keyless tests go on a high port like 8090, killed immediately; never 8078/8099).
- Wants both a full transcript AND a synthesized decision memo (pros/cons/reasoning/downsides) — DONE.
- Communication: enthusiastic, non-defensive about bugs, expects honesty about what's verified vs not. Holds a high "Palantir / Minority Report" aesthetic bar (from BRANCHSCAPE).

**Process lesson for the next session:** Parallel tool batches that mix Write + Bash repeatedly got CANCELLED by the node segfault tripping the whole group, and a few `Edit`s silently failed on string mismatch (always read-back-verify after Write/Edit). Prefer smaller batches; isolate node calls; verify each file landed.

---

## How to Continue

### Immediate Next Steps
1. **First:** Greet the user and confirm they want to proceed with the **bank-profile setup panel** (they approved it, then said "wait for instructions"). Do NOT auto-build.
2. **Then (if yes):** Design the `profile` object (name, type, asset_size, region, values[], mandate). Thread it: `council/live.js` `start(profile, mandate)` → POST `/control` → `make_runner(profile, mandate)` → `Orchestrator.run(mandate, profile)` → prepend a profile preamble to each agent's `ROLE_PROMPTS`. TDD the prompt-assembly in Python first (keyless).
3. **Then:** Build the setup-panel UI in `council.html?live` (archetype preset buttons + editable fields + "Convene the council"). Seed 3 archetypes (Community ~$800M, Rural ag, mid-size Commercial).
4. **Separately, soon:** Capture a good REAL run and `cp "$(ls -t runs/run-*.jsonl | head -1)" runs/golden.jsonl` to bake the offline fallback.

### Commands to Run on Startup
```bash
cd "/Users/cgart/Penn Dropbox/Claudine Gartenberg/Feedforward/playground/orgscience/branchscape"
cat HANDOFF.md
cat ../CLAUDE.md                                   # project instructions (orgscience root)
git log --oneline -8
python3 -m unittest discover -s council_server -p "*_test.py"   # confirm 29 OK
```

### Open Questions
- [ ] Exact archetype preset values (asset sizes, "values" wording) — propose, let user tune.
- [ ] Should the bank profile also bias which tracts agents favor, or only their rhetoric? (Likely rhetoric/priorities via prompts; data stays real.)
- [ ] When to merge `design/the-council` → main and/or deploy to GitHub Pages (public build is replay-only, no key).

### Session Goals (Recommended)
**Primary:** Bank-profile setup panel (agents reason AS the presenter's bank).
**Secondary:** Bake `runs/golden.jsonl` from a real run; optionally start P2c (web_search + map_action).
**Avoid:** Re-touching the orchestrator stall fix or report feature (done + tested). Don't rebuild Phase-1 deterministic mode (it's the intentional fallback).

---

## Reference

### Key Documentation
- `docs/superpowers/specs/2026-05-31-the-council-live-phase2-design.md` — Phase-2 design (architecture, agents, tools, beats, reliability, phasing P2a–P2d)
- `docs/superpowers/plans/2026-05-31-the-council-live-phase2ab.md` — the 12-task P2a+P2b plan (mostly done)
- `README.md` — has a "THE COUNCIL: Live (Phase 2)" run/replay/test/fallback section
- Memory file (auto-loaded): `~/.claude/projects/-Users-cgart-.../memory/the-council-demo.md` — running status log
- `../CLAUDE.md` — orgscience project instructions (superpowers workflow: brainstorm→write-plan→tdd→debug→verify)

### Available Skills (superpowers workflow — the user expects these)
- `/superpowers-brainstorm` — before any feature (used for the pivot)
- `/superpowers-write-plan` — turn spec into bite-sized tasks
- `/superpowers-debug` — root-cause before fixing (used for the stall — pulls evidence from `runs/*.jsonl`)
- `/superpowers-tdd`, `/superpowers-verify`

### Common Commands
```bash
# Real demo (after killing strays):
python3 -m council_server 8099   # → http://127.0.0.1:8099/council.html?live

# Keyless dry run (flow only, canned text — use a THROWAWAY port):
COUNCIL_FAKE=1 python3 -m council_server 8090

# Inspect a run log:
python3 -c "import json;[print(json.loads(l)['type']) for l in open('runs/run-XX>.jsonl')]"

# Replay the golden run (once baked): POST {"action":"replay"} to /control
```

---

## Session Metadata
- **Key Topics:** real multi-agent orchestration, SSE streaming, Claude Messages API tool-use loop, the stall root-cause, transcript+decision-memo report, port/fake-mode confusion.
- **Current HEAD:** `6c56a3c` on `design/the-council`. Tree clean. 29 server + 7 reducer + Phase-1 JS tests all pass.
- **The one real run to treasure:** `runs/run-1780262035.jsonl` (the "amazing" rich deliberation — quality benchmark + stall evidence).
