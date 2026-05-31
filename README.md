# BRANCHSCAPE

A cinematic, presenter-driven visualization of bank-branch **deposit topography** for
Maricopa County, AZ (Phoenix metro), built for a live demo to ABA member bankers.
Every tower is a real bank branch; height + heat = deposits. Plays a 30-year
time-lapse (1994 → 2024) showing deposits 8× while branch count peaks (~880 in 2010)
and thins to 675 — the digital-banking consolidation story, made physical.

Self-contained: this folder can be copied/moved anywhere.

**Live:** https://cgartenberg-ai.github.io/branchscape/  (GitHub Pages, repo
`cgartenberg-ai/branchscape`). To update it after editing: `git add -A && git commit
-m "..." && git push` — Pages rebuilds in ~1 min. The street basemap needs internet;
append `?offline` for a zero-network fallback (no basemap).

## Run it

```bash
cd branchscape
python3 -m http.server 8000
# open http://localhost:8000
```

All runtime libraries and fonts are vendored under `vendor/`, so there are **no CDN
dependencies**. The only thing that touches the network is the online basemap (CARTO
dark tiles).

### Two modes
- **`http://localhost:8000/`** — online: dark CARTO street/label basemap under the towers.
- **`http://localhost:8000/?offline`** — pure void (no basemap): zero network, guaranteed
  to run at any venue. Looks intentionally Palantir-like. The app also **auto-falls back**
  to the void if the online basemap fails to load within 6 s.

## Presenter controls
| Action | Control |
|---|---|
| Play / pause time-lapse | **Space**, or the ❚❚/▶ button |
| Step one year | **← / →**, or the ◀ ▶ buttons |
| Scrub years | click or drag the **timeline** |
| Inspect a branch | **click a tower** → glass panel: branch deposits + trajectory, and parent-institution financials |
| Recolor towers | *Deposits / Bank / Type* control (top-left): deposit heat, by bank owner, or national-vs-community/regional |
| Toggle community-wealth heat field | **W**, or the *Community wealth* button |
| Toggle all-lender small-business lending | **S**, or the *Small-biz lending* button (CRA total $ by tract) |
| Show a bank's lending footprint | open a branch card → *Show lending footprint* (that bank's HMDA mortgage lending by tract, vs its deposit towers) |
| Project a branch forward | open a branch card → *Project 10 years forward* → adjustable income / household / competition sliders, transparent growth formula |
| Replay the cinematic cold open | **R**, or *Replay intro* |

## Data sources (all free, no API key)
- **Branches & deposits** — FDIC Summary of Deposits (`banks.data.fdic.gov/api/sod`).
  The only public dataset with per-branch coordinates + deposits (also carries each
  branch's CERT + bank name). → `fetch_sod.py`
- **Institution financials** — FDIC financials API (`api.fdic.gov/banks/financials`):
  per-bank assets, deposits, C&I (business) loans, 1-4 family mortgages, gross loans,
  ROA. Shown on the branch card as PARENT-institution figures. → `fetch_financials.py`
- **Mortgage lending (HMDA)** — CFPB HMDA Data Browser (2023): originations by
  lender × census tract for Maricopa. Powers the per-bank lending-footprint overlay
  and the card's mortgage figures. → `fetch_hmda.py`
- **Small-business lending (CRA), per bank** — FFIEC CRA disclosure D1-1 (2023):
  each reporter's small-business originations (county-level). → `fetch_cra.py`
- **Small-business lending (CRA), all-lender by tract** — FFIEC CRA aggregate A1-1
  (2023): total small-business $ per census tract, summed across all reporters.
  Powers the *Small-biz lending* tract overlay. → `fetch_cra_aggr.py`
- **Community wealth** — IRS SOI ZIP-code data (`21zpallagi.csv`): average AGI per
  return per ZIP. → `fetch_income.py`
- **Geo centroids** — Census 2023 Gazetteer: ZCTA (`fetch_income.py`) and census
  tract (`fetch_hmda`/overlay) centroids.

> **Granularity caveats for a banker audience — say these out loud:**
> - Branch-level public data is *deposits only* (FDIC SOD).
> - **HMDA** mortgages ARE per-lender × tract → real lending footprint by tract.
> - **CRA** small-business is per-lender **by county only** (tract-level CRA exists
>   solely as all-lender aggregates), so the card's CRA figure is each bank's
>   *Maricopa-county* total.
> - Community banks under ~$1.5B assets don't file CRA. Rather than show them as
>   zero, their small-business lending is **imputed** from the county
>   small-business-per-deposit ratio of reporting banks × that bank's deposits, and
>   flagged **"(est)"**. The card's parent-institution block (assets, C&I, ROA, etc.)
>   is whole-bank, clearly labeled "Parent institution."

### Regenerate data
```bash
# 1. branches + deposits (FDIC SOD), then wrap JSON -> JS global
python3 fetch_sod.py
python3 -c "import json;d=json.load(open('data/branches.json'));open('data/branches.js','w').write('window.BRANCH_DATA='+json.dumps(d,separators=(',',':'))+';')"
python3 fetch_financials.py # -> data/financials.js
python3 fetch_income.py     # -> data/income.js  (+ ZIP centroids)

# 2. lending: raw files first (FFIEC CRA is Cloudflare-gated, so use the Wayback
#    mirror; HMDA's CFPB host blocks Python's TLS, so fetch the CSV with curl)
mkdir -p data/raw
curl -sL 'http://web.archive.org/web/20250315120531id_/https://www.ffiec.gov/cra/xls/23exp_discl.zip' -o data/raw/cra23_discl.zip
curl -sL 'http://web.archive.org/web/2id_/https://www.ffiec.gov/cra/xls/23exp_trans.zip' -o data/raw/cra23_trans.zip
curl -sL 'http://web.archive.org/web/20250321122447id_/https://www.ffiec.gov/cra/xls/23exp_aggr.zip' -o data/raw/cra23_aggr.zip
(cd data/raw && unzip -o cra23_discl.zip && unzip -o cra23_trans.zip && unzip -o cra23_aggr.zip)
curl -sL 'https://ffiec.cfpb.gov/v2/data-browser-api/view/filers?years=2023&counties=04013' -o data/raw/hmda_filers.json
curl -sL 'https://ffiec.cfpb.gov/v2/data-browser-api/view/csv?years=2023&counties=04013&actions_taken=1' -o data/raw/hmda_maricopa.csv
python3 fetch_hmda.py       # -> data/hmda.js
python3 fetch_cra.py        # -> data/cra.js       (per-bank, county-level)
python3 fetch_cra_aggr.py   # -> data/cra_tract.js (all-lender, tract-level)
# data/raw/ is large (~450MB unzipped); safe to delete after the .js files exist.
```
To target a **different metro**, edit the bounding box / county FIPS in the fetchers
(`04013` = Maricopa), rerun, and adjust `CENTER` in `index.html`.

## Design decisions worth keeping
- **Winsorized linear** tower height (cap at the 96th percentile), *not* log. Log made
  every tower look identical; raw linear let one $19B booking branch flatten the rest.
- **Stable branch roster** keyed by location so towers **morph** year-to-year (new ones
  rise, closed ones sink) instead of regrowing from zero each frame.
- Income heat weight is also winsorized ($200k cap) so Paradise Valley's ~$1M-AGI ZIP
  doesn't compress every other neighborhood into one color.

## THE COUNCIL (Act 2) — multi-agent branch-siting demo

Open `council.html` (same server as BRANCHSCAPE). Six AI agents — Chair, Market
Analyst, Risk Officer, Community/CRA Officer, Real-Estate Scout, and a Devil's
Advocate — deliberate live over the Maricopa map to decide where to open the next
branch, in five beats: pose the mandate → gather data → opening positions →
cross-examination → the vote.

- **Run:** `python3 -m http.server 8000` → open `http://localhost:8000/council.html`
  (append `?offline` for the zero-network void — recommended for the venue).
- **Presenter controls:** **Space** play/pause · **→** step one line · **R** replay ·
  type in the bottom bar and hit **Enter / Redirect** to re-pose the question or steer
  the council (e.g. "prioritize underbanked communities", "consider a rural town",
  "weight cost higher"). The room controls the question; the council re-deliberates
  live and the ranking visibly responds.
- **What's real vs modeled:** deposit gap, branch saturation, and community/CRA need
  come from FDIC SOD + FFIEC CRA + IRS income (the same data as Act 1); **growth and
  cost are modeled proxies** and are flagged as such. The Devil's Advocate attacks the
  front-runner's genuinely weakest signal, and the confidence meter drops for real.
- **Architecture:** a deterministic, offline client-side engine (`council/engine.js`)
  computes the ranking/confidence/votes; the HUD (`council/ui.js`) + director
  (`council/director.js`) render and choreograph it over the deck.gl map
  (`council/map.js`); the deliberation wording is the static script
  (`council/script.js`). Nothing about the decision or visuals needs the network.
- **Tests:** `./run-tests.sh` (zero dependencies). NOTE: this machine's Node segfaults
  on teardown, so tests run via `council/_harness.js` and gate on the durable
  `council/.last-test-result` file, not the exit code — see that file's header.
- Phase 2 (live agent voices via a local helper) and Phase 3 (analog metros) are
  separate, later additions.

## Possible next layers
- **THE COUNCIL Phase 2:** live agent voices via a tiny local `council_server.py`
  (`/voice` endpoint, API key server-side only); public build stays static.
- **THE COUNCIL Phase 3:** pre-load 3–5 analog metros (rerun the fetchers per county
  FIPS) + place-name labels, so "name your market type" lights up a real comparable.
- **PMTiles** local basemap extract for offline mode *with* streets/labels.
- Other metros: rerun the fetchers with a different county FIPS / bbox.
- Multi-year HMDA/CRA so the lending overlays animate alongside the deposit time-lapse.
