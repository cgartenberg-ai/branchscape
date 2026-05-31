# THE COUNCIL — Design Spec

*A BRANCHSCAPE Act 2: an AI team deciding where to open the next bank branch — live, on stage, for ~400 ABA regional bankers.*

- **Date:** 2026-05-31
- **Status:** Approved design → ready for implementation plan
- **Runway:** ~1–2 weeks (as of 2026-05-31). Phase 1 is the must-have to build-to-polish and rehearse; Phase 2 only if Phase 1 is solid; Phase 3 only with slack.
- **Repo:** `branchscape/` (self-contained, movable, GitHub Pages–deployed)

---

## 1. Context & Vision

BRANCHSCAPE (Act 1) is a cinematic deck.gl "deposit topography" of Maricopa County, AZ — every glowing tower a real bank branch, a 30-year time-lapse of the digital-banking consolidation story. It already ships with real public data (FDIC SOD, HMDA, CRA, IRS income), vendored libraries, presenter controls, an offline mode, and a transparent forward-projection growth formula.

**THE COUNCIL is Act 2.** On the same map the room just fell in love with, six AI specialists take a decision normally made by a human committee — *"Where do we open the next branch?"* — and the audience watches them gather their own data, argue, get redirected by the room, and reach a verdict they visibly **change their minds** to reach.

**The single design thesis:** the wow is not the *correctness* of the banking decision — it's watching a team with distinct expertise pull real data, disagree, move each other, respond to the audience, and converge, **live and transparently.** Everything below serves that.

### Why this scenario (uncanny-valley reasoning)
A loan-approval, fraud/SAR, or foreclosure-workout scenario would (a) invite domain experts in the room to nitpick the substance instead of being wowed, and (b) drag in regulatory third rails (fair lending, AML, consumer harm) that read as *alarming* to a banking-and-compliance audience. Branch siting threads the needle: recognizable as a committee decision, but bankers aren't site-selection experts (they watch, they don't red-pen), and the framing is **optimistic growth**, not consumer harm. It also sits directly on top of BRANCHSCAPE for maximum production value.

---

## 2. Goals & Non-Goals

**Goals**
- Floor a 400-person banking audience with visible, legible multi-agent collaboration.
- Reuse BRANCHSCAPE's map, data, and aesthetic; ship as a self-contained, movable, offline-safe page.
- Let the presenter pose the question and steer the council at any moment — including typing a real audience member's situation.
- Be genuinely data-driven and intellectually honest (label modeled signals; ground the Devil's Advocate's attacks in real data).

**Non-Goals (YAGNI)**
- No audience-phone / QR participation (network + chaos risk at 400 people; presenter-driven instead).
- No live fetching of an arbitrary bank's private data on stage.
- No real commercial-real-estate listings feed (cost is a transparent modeled proxy).
- No attempt to make the decision "auditably correct" for production lending use — this is an educational showcase.

---

## 3. Success Criteria
- The full 5-beat show runs start-to-finish **with zero network** (offline fallback) and never visibly stalls.
- A first-time viewer can, at any instant, tell **who is speaking, what data they're citing, and where the team stands** — from a stage, at a glance.
- The presenter can interrupt mid-deliberation, type a steer or an audience question, and the council **re-deliberates and the ranking visibly responds** within a few seconds.
- At least one moment where the **team's confidence meter visibly moves** because an agent (esp. the Devil's Advocate) changed the others' minds.

---

## 4. The Decision Domain

**Question template:** *"Open one new branch in [metro] — balance [objective A] with [objective B], subject to [constraint]."*
Default mandate: *"Open one new branch in Maricopa County — balance deposit growth with community access."*

**Candidate zones:** census tracts in the county (we have tract centroids and per-tract CRA data). The engine scores every tract; the Real-Estate Scout "drops a pin" at the centroid of the top zone(s). The shortlist surfaced on stage is the top 2–3.

---

## 5. Architecture Overview (Hybrid)

Three layers, with a strict reliability rule: **the decision and the visuals never depend on the network; only the *wording* of live responses does.**

1. **Decision engine (deterministic, client-side JS).** Scores candidate zones on real signals weighted by the mandate → ranking, confidence, votes, and the Devil's Advocate's counter-signal. This is the source of truth for *what* the council concludes. Bulletproof, offline, fast.
2. **Voice layer (two sources, same interface).**
   - *Static script* — a complete pre-written deliberation, always present, instant, offline. The default on the public GitHub Pages build.
   - *Live helper* — a tiny local server on the stage laptop that calls Claude to generate an agent's line from the current data signals + mandate + deliberation state. Used for novel audience questions. **Falls back to the static script** on any error/timeout.
3. **Presentation layer (the council-of-light UI + director).** Renders the map, the six agents, the spotlight, the meters, and runs the 5-beat choreography and presenter controls.

```
mandate / steer ──▶ Decision Engine ──▶ ranking, confidence, votes, DA counter-signal
                          │                         │
                          ▼                         ▼
                    Voice layer ◀── state ──▶ Presentation layer (UI + director)
                   (live helper or                 │
                    static script)                 ▼
                                            council-of-light on the map
```

---

## 6. The Six Agents

Each agent **owns one or two real data signals**; its position and votes derive from those signals (not free-floating opinion). This keeps the deliberation grounded and lets the engine drive truthfully.

| Agent | Icon | Expertise | Owned signal(s) |
|---|---|---|---|
| **Chair / President** | ⚖️ | synthesis, calls the vote | the composite ranking + agreement |
| **Market Analyst** | 📈 | deposit gaps, household growth | deposit-gap signal; modeled growth |
| **Risk Officer** | 🛡️ | competition, saturation | branch saturation near a zone |
| **Community / CRA Officer** | 🤝 | underbanked access | LMI proxy + per-tract small-biz lending gap |
| **Real-Estate Scout** | 💵 | sites, cost, feasibility | candidate-zone pin + modeled cost |
| **Devil's Advocate** | 😈 | attacks the front-runner | the strongest *counter-signal* against #1 |

The Devil's Advocate sits in its own "challenger's seat," visually distinct (red). Its job is anti-groupthink: find the front-runner's weakest real dimension and force the team to price it in.

---

## 7. The Decision Engine

### 7.1 Signals (per candidate tract)
All derived from data already loaded by BRANCHSCAPE, with modeled signals clearly labeled — same honesty discipline BRANCHSCAPE already uses for imputed CRA.

| Signal | Source | Notes |
|---|---|---|
| **Deposit gap** | FDIC SOD deposits (`BRANCH_DATA`) allocated to nearby tracts vs an income/activity demand proxy | low captured-per-demand = opportunity. *(partly modeled)* |
| **Saturation** | count of branches within radius of tract centroid (`BRANCH_DATA`) | real |
| **Community need** | per-tract all-lender small-business lending (`cra_tract`) + income proxy (`income`) | low lending + below-median income = underserved. real + *(LMI proxy)* |
| **Growth** | modeled momentum proxy from available signals (and/or multi-year SOD) | **labeled "(modeled)"** |
| **Cost / feasibility** | modeled from area income as a rent proxy | **labeled "(modeled)"** — no free CRE feed exists |

### 7.2 Scoring
`score(zone) = Σ wᵢ · normalize(signalᵢ)` where weights `wᵢ` come from the mandate (e.g., "balance deposit growth with community access" → up-weight deposit-gap and community-need). Normalization is winsorized (BRANCHSCAPE's established practice) so no single extreme dominates.

### 7.3 Confidence meter
A function of (a) the **margin** between the #1 and #2 zone scores and (b) **agent agreement** (how many agents' thresholds the front-runner satisfies). When the Devil's Advocate lands a counter-signal, the engine applies a penalty to the front-runner's weak dimension and **recomputes** — the meter drops, and the ranking may reorder. This is the on-stage "they changed their mind" moment, and it is real.

### 7.4 Voting & verdict
Each agent votes yes / conditional / no on the front-runner based on whether it clears that agent's owned-signal threshold. The Chair tallies → recommendation + final confidence. **Dissent is preserved**: the Devil's Advocate's caveat appears on the decision card (intellectual honesty as a feature).

### 7.5 Devil's Advocate counter-signal
For the current front-runner, find its weakest dimension or a strong negative (high nearby saturation = cannibalization; high modeled cost; thin growth). The DA attacks **that real signal**. An optional small curated "events" layer (e.g., a competitor expansion) may add drama but must be flagged as scenario data, not presented as live fact.

---

## 8. Data Sources & Reuse

**Reused from BRANCHSCAPE (no refetch):** `BRANCH_DATA` (branches + deposits + coords), `cra_tract` (per-tract small-biz lending), `income` (ZIP AGI), tract/ZIP centroids, deck.gl + maplibre vendored libs, the dark-void aesthetic, `?offline` mode.

**New:** the per-tract scoring outputs (computed at runtime in JS), the static deliberation script(s), and (Phase 3) additional metros' data globals produced by re-running the existing fetchers with new county FIPS/bbox.

**Honesty labels carried onto the UI:** any modeled signal renders with a "(modeled)" / "(est)" tag, matching BRANCHSCAPE's existing convention so a banker audience trusts what they see.

---

## 9. Visual Language — The Council of Light

*(Locked during brainstorm; animated mockup at `/tmp/sp-slides/council-ring.html`.)*

- **Council of light around the living map.** The six agents are luminous nodes arranged around the central Maricopa map (the "table"). The map stays the hero.
- **Active-speaker spotlight.** Only the speaking agent is lit, enlarged, and haloed, with a **beam to the point on the map** it references. The other five recede to dim glowing nodes. This is the anti-clutter device that keeps six agents legible from a stage.
- **Reaction badges.** Each non-speaking node shows a tiny live ✓ / ✕ / … so you feel all six minds reacting without reading six paragraphs.
- **Confidence meter.** Top-right; moves live as the deliberation shifts.
- **Floating data-chips.** The data an agent gathers appears as chips on the map ("Buckeye HH +41k since 2019", "Tract LMI · CRA-eligible").
- **Devil's Advocate red attack-beam.** When the DA challenges the front-runner, a red beam lances across the map and the meter drops.
- **Lower-third caption.** The current speaker's line, with a typing caret.
- **Redirect bar.** Across the bottom — for posing the question and steering.
- **Aesthetic bar:** Palantir / Minority Report — dark void, data-as-light, additive glow, HUD chrome, eased cinematic motion. *Not* a vibe-coded dashboard.

---

## 10. Choreography — The 5-Beat Show (≈4–6 min)

A director (state machine) sequences beats; the presenter can pause, step, or interrupt at any point.

1. **Pose the mandate.** Presenter (or a captured audience question) sets the question. Map sits dark and ready.
2. **Independent data-gathering.** All six light up in turn and pull their own data onto the map — deposit-gap heat blooms, saturation overlay, LMI/CRA tracts, candidate pins with cost. Data-chips fly in. *("They're actually working.")*
3. **Opening positions.** Each agent states a one-liner and nominates a zone; 2–3 candidate rings compete; the confidence meter appears.
4. **Cross-examination — the climax.** Agents challenge each other; the **Devil's Advocate lances the front-runner**; the confidence meter swings; the ranking may reorder.
5. **Audience redirect → re-deliberation → verdict.** The room steers them; the engine **re-scores live**; a new front-runner may emerge; the **Chair calls the vote** — each agent's vote lights up, the winning zone pulses, dissent is preserved, and a decision card explains the *why*.

---

## 11. Interaction Model (Presenter-Driven, Anytime Interrupt)

- The **presenter holds the controls** (keyboard + click + a text field). No audience phones.
- **Anytime interrupt:** the presenter can pause and steer at any moment, not just a scripted beat. Steers include quick presets ("weight community access higher", "consider a rural zone", "veto the front-runner") and a **freeform text field**.
- **Take a real audience question.** The presenter types an audience member's real situation (bank size, market type, goal, constraint) as the mandate. **The audience controls the question; we control the data** — the council always reasons over pre-loaded data and explicitly *translates* the audience's case onto the map.
- **Analog metros (Phase 3).** 3–5 pre-loaded representative markets (e.g., rural county, sunbelt-boom metro, midwest mid-size). When an audience member names their market *type*, the presenter switches to a real comparable map.

---

## 12. Live Voices (Phase 2)

- **`council_server.py`** — a tiny local server (Python, matching the existing stack) that both **serves the page** and exposes a **`POST /voice`** endpoint.
- `/voice` receives `{agent, role, mandate, signals, state}` and returns that agent's line, generated by Claude with a structured, role-specific prompt grounded in the supplied data signals. The **API key lives only in the server's environment** — never in the page.
- **Fallback:** any error, timeout (short, e.g. ~2–3s), or "helper not running" → the page silently uses the **static script**. The show never waits on the network.
- The **public GitHub Pages build is static-only** (no helper, no key). The live helper is a stage-laptop convenience.

---

## 13. Reliability & Venue Safety

- **Offline-first:** the entire 5-beat show runs with `?offline` (no basemap, no network), exactly like BRANCHSCAPE. Live voices degrade gracefully to static.
- **No CDN:** all libraries vendored locally (inherited from BRANCHSCAPE).
- **Deterministic core:** the decision, rankings, and visuals are pure client-side computation — identical every run.
- **One-command launch:** `python3 council_server.py` (live) or the existing static serve / `serve.command` (static).

---

## 14. File / Module Plan

New, inside `branchscape/` (kept self-contained and movable):
- `council.html` — the Act 2 page (council-of-light UI; reuses vendored libs + data globals).
- `council/engine.js` — the deterministic decision engine (signals, scoring, confidence, votes, DA counter-signal).
- `council/director.js` — the 5-beat state machine + presenter controls + interrupt handling.
- `council/ui.js` — the council-of-light rendering (nodes, spotlight, meters, beams, chips, caption) layered over the deck.gl map.
- `council/script.js` — the static pre-written deliberation(s), keyed by metro/mandate.
- `council/scenarios/` — per-metro scenario config (candidate zones, DA counter-signal, canned lines) — grows in Phase 3.
- `council_server.py` — static file server + `/voice` endpoint (Phase 2).
- `README` additions documenting launch, controls, and the live-helper setup.

Reused unchanged: `vendor/*`, `data/*.js`, the map/camera setup (extracted/shared from `index.html` where practical).

---

## 15. Phasing (runway ~1–2 weeks)

Given the short runway, the plan is ruthless about Phase 1.

- **Phase 1 — The Core Council (Maricopa only). THE PRIORITY.** Council-of-light UI + decision engine + 5-beat director + presenter controls + polished static deliberation + offline-safe. **Independently the wow; the must-have.** Build to polish and **rehearse** before anything else is added.
- **Phase 2 — Live Voices (only if Phase 1 is solid and rehearsed).** `council_server.py` + `/voice` for bespoke live dialogue on novel audience questions, with static fallback already in place.
- **Phase 3 — Analog Metros (only with slack).** Pre-load 3–5 markets via the existing fetchers + a curated scenario each, so "name your market type" lights up a real comparable.

Each phase is independently shippable; if time tightens, **Phase 1 alone is a complete, jaw-dropping demo** — that is the whole point of the phasing.

---

## 16. Open Questions / Risks
- **Modeled growth & cost proxies** must be defensible enough for a banker audience — finalize the exact proxy formulas during Phase 1 and label them clearly. (Risk: a banker challenges the number; mitigation: transparency + "(modeled)" labels + grounding in the visible formula, as BRANCHSCAPE already does.)
- **Tract-level demand allocation** (deposits/income to tracts) is an approximation; pick the simplest defensible method and document it.
- **Live-helper latency** on stage Wi-Fi — keep the timeout short and the fallback seamless; rehearse the failover.
- **Which 3–5 analog metros** best represent the ABA membership — choose during Phase 3 (candidate set: a rural county, a sunbelt-boom metro, a midwest mid-size, a coastal/urban-infill market).

---

## 17. Out of Scope
- Audience-phone / QR interaction.
- Live private-bank data lookup.
- Real CRE listings.
- Production-grade lending/credit decisioning.
