# THE COUNCIL — Phase 1 Implementation Plan (Maricopa Core)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the self-contained, offline-safe "Council of Light" — six AI agents deliberating live over the Maricopa map to decide where to open the next branch — as a complete, rehearsable stage demo.

**Architecture:** A static page (`council.html`) inside the existing `branchscape/` folder reuses the vendored deck.gl/maplibre libs and data globals. A deterministic, pure-JS decision engine scores census tracts on real signals and drives the ranking/confidence/votes (the source of truth). A director (state machine) runs a 5-beat choreography, narrating with a pre-written script and animating a HUD overlay (agent nodes, spotlight, meters, beams, chips) on top of a deck.gl map. No network required.

**Tech Stack:** Vanilla ES2017 JS (no build step, no npm install), deck.gl + maplibre (already vendored), Node's built-in `node:test` + `node:assert` for unit tests (Node v22 present, zero dependencies).

---

## Scope

**This plan is Phase 1 ONLY** — the Maricopa-only core council, which the spec designates as the ruthless priority and an independently jaw-dropping, complete demo. Phase 2 (live voices via `council_server.py`) and Phase 3 (analog metros) are **separate plans** to be written only once Phase 1 is solid and rehearsed. See the spec: `branchscape/docs/superpowers/specs/2026-05-31-the-council-design.md`.

## Testing Approach (read before starting)

This is a no-build vanilla-JS project, so testing is split by what is testable:

- **Logic (engine, mandate, agents, script-coverage)** → real unit tests with `node --test`. These modules are written **dual-mode**: they attach to `window` in the browser AND `module.exports` in Node, so the same file is unit-tested in Node and `<script>`-included in the page. This is where TDD applies — write the failing test first.
- **Visual/interactive (map, ui, director, council.html)** → verified through the **harness preview panel** with concrete, observable expected results (a screenshot showing a specific element, a snapshot containing specific text). These tasks state the exact verification action and what you must observe. There is no DOM unit-test framework; do not invent one.

**Run all unit tests** from `branchscape/`: `node --test council/` (discovers `*.test.js`).

**Preview a page** (used in visual tasks): serve the folder and open the file.
```bash
cd "/Users/cgart/Penn Dropbox/Claudine Gartenberg/Feedforward/playground/orgscience/branchscape"
python3 -m http.server 8077   # then open http://localhost:8077/council.html
```
Use the `preview_start` + `preview_screenshot`/`preview_snapshot` tools against that URL.

## File Structure (Phase 1)

All new files live under `branchscape/` to keep the folder self-contained and movable.

| File | Responsibility |
|---|---|
| `council.html` | Page shell: includes vendored libs + data globals + all `council/*.js`; hosts the map container and the HUD overlay root; boots the director. **No logic.** |
| `council/agents.js` | The 6-agent roster config (id, name, icon, color, role, owned signal, vote threshold). Dual-mode. |
| `council/engine.js` | Pure decision engine: `buildZones`, `normalizeZones`, `scoreZones`, `rankZones`, `computeConfidence`, `computeVotes`, `devilsChallenge`, `applyChallenge`, `haversineKm`. Dual-mode. |
| `council/mandate.js` | `parseMandate(text)` → `{weights, label, flags}`. Dual-mode. |
| `council/script.js` | Static pre-written deliberation content (`window.COUNCIL_SCRIPT`): per-beat, per-agent lines for the default Maricopa mandate. Dual-mode (for coverage test). |
| `council/map.js` | deck.gl map for the council: towers (2024 deposits) + agent overlays (deposit-gap heat, saturation, community/CRA, candidate pins) + `projectToScreen(lngLat)`. Browser-only. |
| `council/ui.js` | The Council-of-Light HUD (DOM): agent nodes, active-speaker spotlight, reaction badges, confidence meter, data-chips, attack-beam, caption, redirect bar. Browser-only. |
| `council/director.js` | The 5-beat state machine + presenter controls + interrupt/redirect. Orchestrates engine + map + ui + script. Browser-only. |
| `council/*.test.js` | Node unit tests for the logic modules. |

**Naming contract (used across tasks — keep exact):**
- Engine namespace: `CouncilEngine` (browser global) / `module.exports` (Node).
- Agents global: `window.COUNCIL_AGENTS` / `module.exports`.
- Mandate global: `window.CouncilMandate` with `.parseMandate`.
- Script global: `window.COUNCIL_SCRIPT`.
- Zone object fields: `{geoid, lon, lat, capturedDeposits, saturation, craAmt, income, depositGap, communityNeed, growth, cost, modeled:[...] , norm:{...}, score}`.
- Signal keys (consistent everywhere): `depositGap`, `growth`, `communityNeed`, `saturation`, `cost`.
- Beats (ids): `mandate`, `gather`, `positions`, `crossExam`, `verdict`.

---

## Task 1: Agent roster config (`council/agents.js`)

**Files:**
- Create: `branchscape/council/agents.js`
- Test: `branchscape/council/agents.test.js`

- [ ] **Step 1: Write the failing test**

```javascript
// branchscape/council/agents.test.js
const test = require('node:test');
const assert = require('node:assert');
const AGENTS = require('./agents.js');

test('roster has the six agents in order', () => {
  assert.strictEqual(AGENTS.length, 6);
  assert.deepStrictEqual(AGENTS.map(a => a.id),
    ['chair', 'market', 'risk', 'community', 'realestate', 'devil']);
});

test('every agent has the required display + logic fields', () => {
  for (const a of AGENTS) {
    for (const k of ['id', 'name', 'icon', 'color', 'role', 'signal']) {
      assert.ok(a[k] !== undefined && a[k] !== '', `${a.id} missing ${k}`);
    }
  }
});

test('specialist agents map to real signal keys; invert flags set', () => {
  const SIGNALS = ['depositGap', 'growth', 'communityNeed', 'saturation', 'cost'];
  const risk = AGENTS.find(a => a.id === 'risk');
  const re = AGENTS.find(a => a.id === 'realestate');
  assert.ok(SIGNALS.includes(AGENTS.find(a => a.id === 'market').signal));
  assert.strictEqual(risk.signal, 'saturation');
  assert.strictEqual(risk.invert, true);   // lower saturation is better
  assert.strictEqual(re.invert, true);      // lower cost is better
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test council/agents.test.js`
Expected: FAIL — `Cannot find module './agents.js'`.

- [ ] **Step 3: Write minimal implementation**

```javascript
// branchscape/council/agents.js
(function (global) {
  const COUNCIL_AGENTS = [
    { id: 'chair',      name: 'Chair / President',      icon: '⚖️', color: '#bfe3ff', role: 'synthesizes · calls the vote', signal: 'composite', threshold: null },
    { id: 'market',     name: 'Market Analyst',         icon: '📈', color: '#7fd3ff', role: 'deposit gaps · growth',        signal: 'depositGap',  threshold: 0.5 },
    { id: 'risk',       name: 'Risk Officer',           icon: '🛡️', color: '#ffb86b', role: 'competition · saturation',     signal: 'saturation',  threshold: 0.5, invert: true },
    { id: 'community',  name: 'Community / CRA Officer', icon: '🤝', color: '#6ad6b0', role: 'underbanked access',           signal: 'communityNeed', threshold: 0.5 },
    { id: 'realestate', name: 'Real-Estate Scout',      icon: '💵', color: '#c89bff', role: 'sites · cost · feasibility',   signal: 'cost',        threshold: 0.5, invert: true },
    { id: 'devil',      name: "Devil's Advocate",       icon: '😈', color: '#ff5a5a', role: 'challenges the front-runner',  signal: 'counter',     threshold: null },
  ];
  if (typeof module !== 'undefined' && module.exports) module.exports = COUNCIL_AGENTS;
  else global.COUNCIL_AGENTS = COUNCIL_AGENTS;
})(typeof window !== 'undefined' ? window : globalThis);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test council/agents.test.js`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add council/agents.js council/agents.test.js
git commit -m "feat(council): agent roster config with unit tests"
```

---

## Task 2: Engine — geo helper + zone building (`council/engine.js`)

**Files:**
- Create: `branchscape/council/engine.js`
- Test: `branchscape/council/engine.test.js`

- [ ] **Step 1: Write the failing test**

```javascript
// branchscape/council/engine.test.js
const test = require('node:test');
const assert = require('node:assert');
const E = require('./engine.js');

// tiny deterministic fixture: 3 tracts, a few branches, cra + income
const FIX = {
  tracts: { A: [-112.00, 33.40], B: [-112.10, 33.50], C: [-112.50, 33.90] },
  branches: [
    { lat: 33.401, lon: -112.001, dep: { '2015': 1000, '2024': 2000 } }, // near A
    { lat: 33.402, lon: -112.002, dep: { '2015': 500,  '2024': 1500 } }, // near A
    { lat: 33.501, lon: -112.101, dep: { '2015': 800,  '2024': 900  } }, // near B
    // none near C
  ],
  craTract: { tracts: { A: { amt: 5000, n: 50 }, B: { amt: 200, n: 5 }, C: { amt: 100, n: 2 } } },
  income: [
    { zip: 'a', lat: 33.40, lon: -112.00, income: 90000 },
    { zip: 'b', lat: 33.50, lon: -112.10, income: 40000 },
    { zip: 'c', lat: 33.90, lon: -112.50, income: 30000 },
  ],
};

test('haversineKm is ~0 for identical points and positive otherwise', () => {
  assert.ok(E.haversineKm(33.4, -112, 33.4, -112) < 0.001);
  assert.ok(E.haversineKm(33.4, -112, 33.5, -112) > 5);
});

test('buildZones aggregates branches, cra, income per tract', () => {
  const zones = E.buildZones(FIX, { radiusKm: 3 });
  assert.strictEqual(zones.length, 3);
  const byId = Object.fromEntries(zones.map(z => [z.geoid, z]));
  assert.strictEqual(byId.A.saturation, 2);
  assert.strictEqual(byId.A.capturedDeposits, 3500);
  assert.strictEqual(byId.B.saturation, 1);
  assert.strictEqual(byId.C.saturation, 0);
  assert.strictEqual(byId.C.capturedDeposits, 0);
  assert.strictEqual(byId.A.craAmt, 5000);
  assert.strictEqual(byId.B.income, 40000); // nearest income point to B
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test council/engine.test.js`
Expected: FAIL — `Cannot find module './engine.js'`.

- [ ] **Step 3: Write minimal implementation**

```javascript
// branchscape/council/engine.js
(function (global) {
  const EARTH_KM = 6371;
  const rad = d => d * Math.PI / 180;
  function haversineKm(aLat, aLon, bLat, bLon) {
    const dLat = rad(bLat - aLat), dLon = rad(bLon - aLon);
    const s = Math.sin(dLat / 2) ** 2 +
      Math.cos(rad(aLat)) * Math.cos(rad(bLat)) * Math.sin(dLon / 2) ** 2;
    return 2 * EARTH_KM * Math.asin(Math.min(1, Math.sqrt(s)));
  }
  const num = v => (typeof v === 'number' && isFinite(v)) ? v : 0;

  // data = { tracts:{geoid:[lon,lat]}, branches:[{lat,lon,dep:{year}}],
  //          craTract:{tracts:{geoid:{amt,n}}}, income:[{lat,lon,income}] }
  function buildZones(data, opts = {}) {
    const radiusKm = opts.radiusKm || 3;
    const latestYear = opts.latestYear || '2024';
    const baseYear = opts.baseYear || '2015';
    const zones = [];
    for (const geoid of Object.keys(data.tracts)) {
      const [lon, lat] = data.tracts[geoid];
      let saturation = 0, capturedDeposits = 0, capturedBase = 0;
      for (const b of data.branches) {
        if (haversineKm(lat, lon, b.lat, b.lon) <= radiusKm) {
          saturation++;
          capturedDeposits += num(b.dep && b.dep[latestYear]);
          capturedBase += num(b.dep && b.dep[baseYear]);
        }
      }
      // nearest income point
      let income = 0, best = Infinity;
      for (const p of data.income) {
        const d = haversineKm(lat, lon, p.lat, p.lon);
        if (d < best) { best = d; income = p.income; }
      }
      const cra = data.craTract.tracts[geoid];
      const craAmt = cra ? cra.amt : 0;
      zones.push({ geoid, lon, lat, saturation, capturedDeposits, capturedBase, craAmt, income });
    }
    return zones;
  }

  const Engine = { haversineKm, buildZones };
  if (typeof module !== 'undefined' && module.exports) module.exports = Engine;
  else global.CouncilEngine = Engine;
})(typeof window !== 'undefined' ? window : globalThis);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test council/engine.test.js`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add council/engine.js council/engine.test.js
git commit -m "feat(council): engine zone-building over branches/cra/income"
```

---

## Task 3: Engine — derived signals + winsorized normalization

**Files:**
- Modify: `branchscape/council/engine.js`
- Modify: `branchscape/council/engine.test.js`

- [ ] **Step 1: Write the failing test (append)**

```javascript
test('deriveSignals produces the five signal keys, modeled flags labeled', () => {
  const zones = E.deriveSignals(E.buildZones(FIX, { radiusKm: 3 }));
  const z = zones[0];
  for (const k of ['depositGap', 'growth', 'communityNeed', 'saturation', 'cost']) {
    assert.strictEqual(typeof z[k], 'number', `missing signal ${k}`);
  }
  assert.ok(z.modeled.includes('growth'));
  assert.ok(z.modeled.includes('cost'));
});

test('normalizeZones maps each signal to 0..1 (winsorized) under z.norm', () => {
  const zones = E.normalizeZones(E.deriveSignals(E.buildZones(FIX, { radiusKm: 3 })));
  for (const z of zones) {
    for (const k of ['depositGap', 'growth', 'communityNeed', 'saturation', 'cost']) {
      assert.ok(z.norm[k] >= 0 && z.norm[k] <= 1, `${k} out of range: ${z.norm[k]}`);
    }
  }
  // tract C (no branches, low income, low cra) should have the highest community need
  const byId = Object.fromEntries(zones.map(z => [z.geoid, z]));
  assert.ok(byId.C.norm.communityNeed >= byId.A.norm.communityNeed);
  // tract A (2 branches) is the most saturated
  assert.ok(byId.A.norm.saturation >= byId.B.norm.saturation);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test council/engine.test.js`
Expected: FAIL — `E.deriveSignals is not a function`.

- [ ] **Step 3: Implement (add to engine.js before the `Engine` object, then add to the object)**

```javascript
  // Derived signals. depositGap & communityNeed grounded; growth & cost modeled.
  function deriveSignals(zones, opts = {}) {
    const k = 1; // smoothing for ratios (deposits in $k)
    const incomes = zones.map(z => z.income).sort((a, b) => a - b);
    const medianIncome = incomes[Math.floor(incomes.length / 2)] || 0;
    return zones.map(z => {
      // opportunity: lots of income/demand, little captured deposit
      const depositGap = z.income / (z.capturedDeposits + k);
      // modeled momentum: recent vs base deposits near the zone
      const growth = z.capturedDeposits / (z.capturedBase + k);
      // underserved: low small-biz lending AND below-median income
      const incomeNeed = medianIncome > 0 ? Math.max(0, (medianIncome - z.income) / medianIncome) : 0;
      const craNeed = 1 / (z.craAmt + k);
      const communityNeed = 0.5 * incomeNeed + 0.5 * craNeed;
      // modeled cost proxy: higher-income areas cost more to enter
      const cost = z.income;
      return Object.assign({}, z, {
        depositGap, growth, communityNeed,
        saturation: z.saturation, cost,
        modeled: ['growth', 'cost'],
      });
    });
  }

  function winsor(values, p = 0.05) {
    const s = [...values].sort((a, b) => a - b);
    const lo = s[Math.floor(p * (s.length - 1))];
    const hi = s[Math.ceil((1 - p) * (s.length - 1))];
    return { lo, hi };
  }
  function normalizeZones(zones) {
    const keys = ['depositGap', 'growth', 'communityNeed', 'saturation', 'cost'];
    const bounds = {};
    for (const key of keys) bounds[key] = winsor(zones.map(z => z[key]));
    return zones.map(z => {
      const norm = {};
      for (const key of keys) {
        const { lo, hi } = bounds[key];
        norm[key] = hi > lo ? Math.min(1, Math.max(0, (z[key] - lo) / (hi - lo))) : 0;
      }
      return Object.assign({}, z, { norm });
    });
  }
```

Add `deriveSignals, normalizeZones` to the exported `Engine` object:
```javascript
  const Engine = { haversineKm, buildZones, deriveSignals, normalizeZones };
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test council/engine.test.js`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add council/engine.js council/engine.test.js
git commit -m "feat(council): derived signals + winsorized normalization"
```

---

## Task 4: Engine — scoring, ranking, confidence, votes

**Files:**
- Modify: `branchscape/council/engine.js`
- Modify: `branchscape/council/engine.test.js`

- [ ] **Step 1: Write the failing test (append)**

```javascript
const AGENTS = require('./agents.js');

const COMMUNITY_WEIGHTS = { depositGap: 1, growth: 0.5, communityNeed: 2, saturation: 1, cost: 0.5 };

function rankedFix(weights) {
  return E.rankZones(E.normalizeZones(E.deriveSignals(E.buildZones(FIX, { radiusKm: 3 }))), weights);
}

test('rankZones sorts by weighted score, descending', () => {
  const ranked = rankedFix(COMMUNITY_WEIGHTS);
  for (let i = 1; i < ranked.length; i++) {
    assert.ok(ranked[i - 1].score >= ranked[i].score);
  }
  // community-weighted mandate should not rank the saturated, high-income tract A first
  assert.notStrictEqual(ranked[0].geoid, 'A');
});

test('computeConfidence returns 0..100 and rises with a bigger margin', () => {
  const ranked = rankedFix(COMMUNITY_WEIGHTS);
  const c = E.computeConfidence(ranked, AGENTS);
  assert.ok(c >= 0 && c <= 100);
});

test('computeVotes yields a yes/conditional/no per specialist agent', () => {
  const ranked = rankedFix(COMMUNITY_WEIGHTS);
  const votes = E.computeVotes(ranked[0], AGENTS);
  const specialists = AGENTS.filter(a => a.threshold !== null);
  assert.strictEqual(votes.length, specialists.length);
  for (const v of votes) assert.ok(['yes', 'conditional', 'no'].includes(v.vote));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test council/engine.test.js`
Expected: FAIL — `E.rankZones is not a function`.

- [ ] **Step 3: Implement (add functions + extend export)**

```javascript
  const DEFAULT_WEIGHTS = { depositGap: 1, growth: 1, communityNeed: 1, saturation: 1, cost: 0.5 };
  // positive signals add; saturation & cost subtract (negatives)
  function scoreZone(z, weights) {
    const w = Object.assign({}, DEFAULT_WEIGHTS, weights);
    const n = z.norm;
    return w.depositGap * n.depositGap
      + w.growth * n.growth
      + w.communityNeed * n.communityNeed
      - w.saturation * n.saturation
      - w.cost * n.cost;
  }
  function rankZones(zones, weights) {
    return zones
      .map(z => Object.assign({}, z, { score: scoreZone(z, weights) }))
      .sort((a, b) => b.score - a.score);
  }
  function agentSatisfied(zone, agent) {
    if (agent.threshold === null) return null;
    const v = zone.norm[agent.signal];
    const eff = agent.invert ? (1 - v) : v;       // inverted: low saturation/cost is "good"
    if (eff >= agent.threshold) return 'yes';
    if (eff >= agent.threshold - 0.2) return 'conditional';
    return 'no';
  }
  function computeVotes(frontRunner, agents) {
    return agents
      .filter(a => a.threshold !== null)
      .map(a => ({ id: a.id, vote: agentSatisfied(frontRunner, a) }));
  }
  function computeConfidence(ranked, agents) {
    if (!ranked.length) return 0;
    const top = ranked[0];
    const margin = ranked.length > 1
      ? Math.max(0, Math.min(1, (top.score - ranked[1].score)))
      : 0.5;
    const votes = computeVotes(top, agents);
    const yes = votes.filter(v => v.vote === 'yes').length;
    const agreement = votes.length ? yes / votes.length : 0;
    const pct = 45 + 35 * margin + 20 * agreement;   // ~45..100
    return Math.round(Math.max(0, Math.min(100, pct)));
  }
```

Extend export:
```javascript
  const Engine = { haversineKm, buildZones, deriveSignals, normalizeZones,
    rankZones, scoreZone, computeVotes, computeConfidence, DEFAULT_WEIGHTS };
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test council/engine.test.js`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add council/engine.js council/engine.test.js
git commit -m "feat(council): scoring, ranking, confidence, votes"
```

---

## Task 5: Engine — Devil's Advocate challenge

**Files:**
- Modify: `branchscape/council/engine.js`
- Modify: `branchscape/council/engine.test.js`

- [ ] **Step 1: Write the failing test (append)**

```javascript
test('devilsChallenge targets the front-runner\'s weakest dimension', () => {
  const ranked = rankedFix(COMMUNITY_WEIGHTS);
  const ch = E.devilsChallenge(ranked, COMMUNITY_WEIGHTS);
  assert.strictEqual(ch.targetGeoid, ranked[0].geoid);
  assert.ok(['depositGap', 'growth', 'communityNeed', 'saturation', 'cost'].includes(ch.dimension));
  assert.ok(ch.penalty > 0);
});

test('applyChallenge lowers the front-runner score and confidence', () => {
  const ranked = rankedFix(COMMUNITY_WEIGHTS);
  const before = E.computeConfidence(ranked, AGENTS);
  const ch = E.devilsChallenge(ranked, COMMUNITY_WEIGHTS);
  const after = E.applyChallenge(ranked, ch);
  const topAfter = after.find(z => z.geoid === ch.targetGeoid);
  const topBefore = ranked.find(z => z.geoid === ch.targetGeoid);
  assert.ok(topAfter.score < topBefore.score);
  assert.ok(E.computeConfidence(after, AGENTS) <= before);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test council/engine.test.js`
Expected: FAIL — `E.devilsChallenge is not a function`.

- [ ] **Step 3: Implement (add + extend export)**

```javascript
  // Find the front-runner's weakest real dimension: lowest positive signal,
  // or highest negative (saturation/cost). Returns a grounded challenge.
  function devilsChallenge(ranked, weights) {
    const top = ranked[0];
    const n = top.norm;
    const candidates = [
      { dimension: 'growth',        bad: 1 - n.growth },        // low growth is bad
      { dimension: 'depositGap',    bad: 1 - n.depositGap },    // thin opportunity is bad
      { dimension: 'communityNeed', bad: 1 - n.communityNeed },
      { dimension: 'saturation',    bad: n.saturation },        // high saturation is bad
      { dimension: 'cost',          bad: n.cost },              // high cost is bad
    ];
    candidates.sort((a, b) => b.bad - a.bad);
    const worst = candidates[0];
    return { targetGeoid: top.geoid, dimension: worst.dimension, penalty: 0.3 + 0.5 * worst.bad };
  }
  // Re-score with the challenged dimension penalized, then re-rank.
  function applyChallenge(ranked, challenge) {
    return ranked
      .map(z => {
        if (z.geoid !== challenge.targetGeoid) return Object.assign({}, z);
        return Object.assign({}, z, { score: z.score - challenge.penalty });
      })
      .sort((a, b) => b.score - a.score);
  }
```

Extend export:
```javascript
  const Engine = { haversineKm, buildZones, deriveSignals, normalizeZones,
    rankZones, scoreZone, computeVotes, computeConfidence, DEFAULT_WEIGHTS,
    devilsChallenge, applyChallenge };
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test council/engine.test.js`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add council/engine.js council/engine.test.js
git commit -m "feat(council): devil's-advocate challenge + re-rank"
```

---

## Task 6: Mandate parsing (`council/mandate.js`)

**Files:**
- Create: `branchscape/council/mandate.js`
- Test: `branchscape/council/mandate.test.js`

- [ ] **Step 1: Write the failing test**

```javascript
// branchscape/council/mandate.test.js
const test = require('node:test');
const assert = require('node:assert');
const M = require('./mandate.js');

test('default mandate balances deposit growth and community access', () => {
  const r = M.parseMandate('Open one new branch in Maricopa — balance deposit growth with community access');
  assert.ok(r.weights.communityNeed >= 1);
  assert.ok(r.weights.depositGap >= 1);
  assert.ok(typeof r.label === 'string' && r.label.length > 0);
});

test('community-first language up-weights communityNeed', () => {
  const base = M.parseMandate('grow deposits aggressively');
  const comm = M.parseMandate('prioritize underbanked communities and CRA access');
  assert.ok(comm.weights.communityNeed > base.weights.communityNeed);
});

test('"rural" sets a flag and de-emphasizes saturation tolerance', () => {
  const r = M.parseMandate('consider a rural town');
  assert.ok(r.flags.includes('rural'));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test council/mandate.test.js`
Expected: FAIL — `Cannot find module './mandate.js'`.

- [ ] **Step 3: Write minimal implementation**

```javascript
// branchscape/council/mandate.js
(function (global) {
  function parseMandate(text) {
    const t = (text || '').toLowerCase();
    const weights = { depositGap: 1, growth: 1, communityNeed: 1, saturation: 1, cost: 0.5 };
    const flags = [];
    if (/communit|underbank|access|cra|lmi|equit/.test(t)) weights.communityNeed += 1.5;
    if (/deposit|growth|profit|return|aggress/.test(t)) { weights.depositGap += 1; weights.growth += 0.5; }
    if (/competition|saturat|cannibal/.test(t)) weights.saturation += 1;
    if (/cost|cheap|budget|lease|rent/.test(t)) weights.cost += 1;
    if (/rural|small town|outlying/.test(t)) { flags.push('rural'); weights.saturation += 0.5; }
    const label = (text && text.trim()) ||
      'Open one new branch in Maricopa — balance deposit growth with community access';
    return { weights, label, flags };
  }
  const Mandate = { parseMandate };
  if (typeof module !== 'undefined' && module.exports) module.exports = Mandate;
  else global.CouncilMandate = Mandate;
})(typeof window !== 'undefined' ? window : globalThis);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test council/mandate.test.js`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add council/mandate.js council/mandate.test.js
git commit -m "feat(council): keyword mandate parser → signal weights"
```

---

## Task 7: Static deliberation script (`council/script.js`)

The director plays these lines when live voices are off (always, in Phase 1). Lines reference data placeholders the director fills from the engine result (e.g., `{front}` = front-runner zone label, `{conf}` = confidence). Keep them punchy and stage-readable.

**Files:**
- Create: `branchscape/council/script.js`
- Test: `branchscape/council/script.test.js`

- [ ] **Step 1: Write the failing test**

```javascript
// branchscape/council/script.test.js
const test = require('node:test');
const assert = require('node:assert');
const SCRIPT = require('./script.js');
const AGENTS = require('./agents.js');

test('script covers all five beats', () => {
  for (const beat of ['mandate', 'gather', 'positions', 'crossExam', 'verdict']) {
    assert.ok(SCRIPT.beats[beat], `missing beat ${beat}`);
  }
});

test('gather + positions have a line for every speaking specialist', () => {
  const speakers = AGENTS.map(a => a.id);
  for (const beat of ['gather', 'positions']) {
    for (const line of SCRIPT.beats[beat]) {
      assert.ok(speakers.includes(line.agent), `unknown agent ${line.agent} in ${beat}`);
      assert.ok(typeof line.text === 'string' && line.text.length > 0);
    }
    const present = new Set(SCRIPT.beats[beat].map(l => l.agent));
    for (const id of ['market', 'risk', 'community', 'realestate']) {
      assert.ok(present.has(id), `${beat} missing specialist ${id}`);
    }
  }
});

test('crossExam includes a devil line and verdict includes the chair', () => {
  assert.ok(SCRIPT.beats.crossExam.some(l => l.agent === 'devil'));
  assert.ok(SCRIPT.beats.verdict.some(l => l.agent === 'chair'));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test council/script.test.js`
Expected: FAIL — `Cannot find module './script.js'`.

- [ ] **Step 3: Write the implementation (complete default-mandate script)**

```javascript
// branchscape/council/script.js
(function (global) {
  // {front}=front-runner label, {runner}=runner-up label, {conf}=confidence%,
  // {dim}=challenged dimension. Director substitutes.
  const COUNCIL_SCRIPT = {
    beats: {
      mandate: [
        { agent: 'chair', text: 'Our mandate: open one branch in Maricopa — balance deposit growth with community access. Team, gather your data.' },
      ],
      gather: [
        { agent: 'market',     text: 'Pulling FDIC deposits by tract — mapping where demand outruns the branches that serve it.' },
        { agent: 'risk',       text: 'Overlaying every competitor branch. I want the saturation picture before anyone falls in love with a site.' },
        { agent: 'community',  text: 'Lighting up the underbanked tracts — low small-business lending, below-median income, CRA-eligible.' },
        { agent: 'realestate', text: 'Dropping candidate pins and pricing each — feasibility is where strategy meets the lease.' },
      ],
      positions: [
        { agent: 'market',     text: '{front} has the widest deposit gap in the county — strong households, thin coverage. That\'s my pick.' },
        { agent: 'community',  text: 'Agreed, and {front} is CRA-eligible. Rare alignment of profit and mission — I support it.' },
        { agent: 'realestate', text: 'Site cost at {front} is reasonable; {runner} is cheaper but the demand isn\'t there. I lean {front}.' },
        { agent: 'risk',       text: 'I\'m cautious. Let me stress-test the front-runner before we commit.' },
      ],
      crossExam: [
        { agent: 'devil',  text: 'Before we celebrate {front} — its weakest dimension is {dim}. Your {conf}% confidence is optimistic until we price that in.' },
        { agent: 'risk',   text: 'The Devil\'s right. Discount the win probability — this isn\'t a layup.' },
        { agent: 'market', text: 'Fair. Even discounted, the deposit gap keeps {front} ahead of {runner} — but the margin is narrower now.' },
      ],
      verdict: [
        { agent: 'chair', text: 'I\'m calling the vote.' },
        { agent: 'chair', text: 'The council recommends {front}, at {conf}% confidence — with the Devil\'s caveat on {dim} noted in the record.' },
      ],
    },
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = COUNCIL_SCRIPT;
  else global.COUNCIL_SCRIPT = COUNCIL_SCRIPT;
})(typeof window !== 'undefined' ? window : globalThis);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test council/script.test.js`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add council/script.js council/script.test.js
git commit -m "feat(council): static deliberation script + coverage test"
```

---

## Task 8: Page shell + map (`council.html`, `council/map.js`)

This task makes a page that loads and renders the Maricopa towers (proving lib + data reuse works), before any HUD/logic is layered on. Browser-verified.

**Files:**
- Create: `branchscape/council.html`
- Create: `branchscape/council/map.js`

- [ ] **Step 1: Create `council/map.js`**

```javascript
// branchscape/council/map.js  (browser-only; relies on deck, BRANCH_DATA, TRACTS)
const CENTER = { longitude: -112.07, latitude: 33.45, zoom: 9.2, pitch: 55, bearing: -17 };
const OFFLINE = location.search.includes('offline');

const CouncilMap = (function () {
  let deckgl;
  const BR = window.BRANCH_DATA.branches;
  const depOf = b => (b.dep && (b.dep['2024'] || 0)) || 0;
  const overlays = { gap: false, saturation: false, community: false };
  let candidatePins = [];
  let zones = [];

  function towerLayer() {
    return new deck.ColumnLayer({
      id: 'towers', data: BR, diskResolution: 6, radius: 90, extruded: true,
      getPosition: b => [b.lon, b.lat],
      getElevation: b => Math.min(depOf(b), 4000000) / 1500,
      getFillColor: () => [127, 211, 255, 180],
      elevationScale: 1, pickable: false,
    });
  }
  function heatLayer(id, signal, rgb) {
    if (!overlays[id]) return null;
    return new deck.ScatterplotLayer({
      id, data: zones, radiusUnits: 'meters', getRadius: 700,
      getPosition: z => [z.lon, z.lat],
      getFillColor: z => [rgb[0], rgb[1], rgb[2], Math.round(40 + 170 * (z.norm ? z.norm[signal] : 0))],
    });
  }
  function pinLayer() {
    return new deck.ScatterplotLayer({
      id: 'pins', data: candidatePins, radiusUnits: 'pixels', getRadius: 14,
      getPosition: z => [z.lon, z.lat],
      getFillColor: [255, 216, 107, 230], stroked: true,
      getLineColor: [255, 216, 107], lineWidthUnits: 'pixels', getLineWidth: 2,
    });
  }
  function render() {
    deckgl.setProps({ layers: [
      towerLayer(),
      heatLayer('gap', 'depositGap', [127, 211, 255]),
      heatLayer('saturation', 'saturation', [255, 184, 107]),
      heatLayer('community', 'communityNeed', [106, 214, 176]),
      pinLayer(),
    ].filter(Boolean) });
  }
  function initMap() {
    deckgl = new deck.DeckGL({
      container: 'map',
      mapStyle: OFFLINE ? null : 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
      initialViewState: CENTER, controller: true,
    });
    render();
  }
  function setZones(z) { zones = z; render(); }
  function dropPins(z) { candidatePins = z; render(); }
  function setOverlay(name, on) { overlays[name] = on; render(); }
  function projectToScreen(lon, lat) {
    const vp = deckgl && deckgl.deck && deckgl.deck.getViewports()[0];
    return vp ? vp.project([lon, lat]) : [0, 0]; // [x,y] px
  }
  return { initMap, setZones, dropPins, setOverlay, projectToScreen, CENTER };
})();
```

- [ ] **Step 2: Create `council.html` (shell that boots the map) and empty stubs**

```bash
echo "// council/ui.js (Task 9)" > council/ui.js
echo "// council/director.js (Task 11)" > council/director.js
```

```html
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>THE COUNCIL — BRANCHSCAPE Act 2</title>
<link rel="stylesheet" href="vendor/fonts.css">
<link rel="stylesheet" href="vendor/maplibre-gl.css">
<script src="vendor/deck.gl.min.js"></script>
<script src="vendor/maplibre-gl.js"></script>
<script src="data/branches.js"></script>
<script src="data/income.js"></script>
<script src="data/cra_tract.js"></script>
<script src="data/tracts.js"></script>
<style>
  html,body{margin:0;height:100%;background:#02040a;color:#dfe8f5;font-family:'Inter',-apple-system,'Segoe UI',sans-serif;overflow:hidden}
  #map{position:fixed;inset:0}
  #hud{position:fixed;inset:0;pointer-events:none}
</style>
</head>
<body>
  <div id="map"></div>
  <div id="hud"></div>
  <script src="council/agents.js"></script>
  <script src="council/engine.js"></script>
  <script src="council/mandate.js"></script>
  <script src="council/script.js"></script>
  <script src="council/map.js"></script>
  <script src="council/ui.js"></script>
  <script src="council/director.js"></script>
  <script>
    CouncilMap.initMap();
    // Director.start() wired in Task 11; map-only smoke test for now.
  </script>
</body>
</html>
```

- [ ] **Step 3: Verify in the preview**

```bash
cd "/Users/cgart/Penn Dropbox/Claudine Gartenberg/Feedforward/playground/orgscience/branchscape"
python3 -m http.server 8077
```
Use `preview_start` → `http://localhost:8077/council.html`, then `preview_screenshot`.
**Expected to observe:** the dark map with glowing blue Maricopa towers (same geography as `index.html`), no console errors.
Also check `preview_console_logs` — **Expected:** no red errors.

- [ ] **Step 4: Verify offline mode**

`preview_start` → `http://localhost:8077/council.html?offline`, then `preview_screenshot`.
**Expected:** towers render on a pure black void (no basemap), no network calls for tiles.

- [ ] **Step 5: Commit**

```bash
git add council.html council/map.js council/ui.js council/director.js
git commit -m "feat(council): page shell + deck.gl map with towers (online+offline)"
```

---

## Task 9: Council-of-Light HUD (`council/ui.js`)

Port the locked mockup into a real, data-driven HUD module. Reads `window.COUNCIL_AGENTS`; renders into `#hud`. Pure presentation — no decisions.

**Files:**
- Modify: `branchscape/council/ui.js`

- [ ] **Step 1: Implement the HUD module**

```javascript
// branchscape/council/ui.js  (browser-only; relies on COUNCIL_AGENTS, CouncilMap)
const CouncilUI = (function () {
  const hud = document.getElementById('hud');
  const nodeEls = {};
  // arc positions (% of viewport) keyed by agent id; devil sits low & apart
  const POS = {
    chair: [50, 12], market: [14, 26], realestate: [86, 26],
    risk: [9, 55], community: [91, 55], devil: [50, 78],
  };
  function el(tag, cls, html) { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }

  function mount() {
    hud.innerHTML = '';
    for (const a of window.COUNCIL_AGENTS) {
      const [x, y] = POS[a.id];
      const n = el('div', 'c-node' + (a.id === 'devil' ? ' c-devil' : ''));
      n.style.cssText = `position:absolute;left:${x}%;top:${y}%;transform:translate(-50%,-50%);width:130px;text-align:center;transition:.3s`;
      n.innerHTML =
        `<div class="c-orb" style="--c:${a.color};width:62px;height:62px;border-radius:50%;margin:0 auto;` +
        `display:flex;align-items:center;justify-content:center;font-size:24px;opacity:.7;` +
        `background:radial-gradient(circle at 38% 32%,rgba(40,70,110,.95),rgba(10,20,38,.95));` +
        `border:1.5px solid ${a.color};box-shadow:0 0 18px ${a.color}55;position:relative">` +
        `${a.icon}<div class="c-react" style="position:absolute;top:-6px;right:18px"></div></div>` +
        `<div style="font-size:11.5px;font-weight:600;margin-top:7px">${a.name}</div>` +
        `<div style="font-size:9.5px;color:#6f88a6">${a.role}</div>`;
      hud.appendChild(n); nodeEls[a.id] = n;
    }
    const meter = el('div', 'c-meter');
    meter.style.cssText = 'position:absolute;top:60px;right:28px;width:210px';
    meter.innerHTML =
      `<div style="font-size:10.5px;color:#8aa0bb;display:flex;justify-content:space-between"><span>TEAM CONFIDENCE</span><span id="c-front"></span></div>` +
      `<div style="height:6px;border-radius:4px;background:#10223a;margin-top:5px;overflow:hidden"><div id="c-fill" style="height:100%;width:0;border-radius:4px;background:linear-gradient(90deg,#ff7e7e,#ffb86b);transition:width .8s"></div></div>` +
      `<div id="c-delta" style="font-size:10.5px;color:#8aa0bb;text-align:right;margin-top:4px"></div>`;
    hud.appendChild(meter);
    const phase = el('div'); phase.id = 'c-phase';
    phase.style.cssText = 'position:absolute;top:22px;right:28px;font-size:13px;color:#ffd86b;font-weight:600;letter-spacing:1px';
    hud.appendChild(phase);
    const cap = el('div'); cap.id = 'c-caption';
    cap.style.cssText = 'position:absolute;left:50%;bottom:120px;transform:translateX(-50%);width:660px;text-align:center';
    cap.innerHTML = `<div id="c-who" style="font-size:11px;letter-spacing:2px;text-transform:uppercase;font-weight:700"></div><div id="c-line" style="font-size:18px;line-height:1.5;margin-top:8px"></div>`;
    hud.appendChild(cap);
    const bar = el('div');
    bar.style.cssText = 'position:absolute;bottom:26px;left:34px;right:34px;height:52px;background:linear-gradient(90deg,rgba(16,28,46,.92),rgba(20,34,56,.92));border:1px solid #234266;border-radius:28px;display:flex;align-items:center;padding:0 22px;gap:14px;pointer-events:auto';
    bar.innerHTML = `<div style="font-size:10.5px;letter-spacing:2px;color:#5b7290;text-transform:uppercase">YOU / THE ROOM ▸</div><input id="c-input" placeholder="Pose the question, or steer the council…  (e.g. weight community higher)" style="flex:1;background:transparent;border:none;outline:none;color:#cfe0f5;font-size:14px;font-style:italic"><div id="c-send" style="background:#1c66ff;color:#fff;font-size:12px;font-weight:600;padding:9px 18px;border-radius:18px;cursor:pointer">Redirect →</div>`;
    hud.appendChild(bar);
  }

  function setPhase(label) { document.getElementById('c-phase').textContent = label; }
  function setActiveSpeaker(agentId, line) {
    for (const id in nodeEls) {
      const orb = nodeEls[id].querySelector('.c-orb');
      const active = id === agentId;
      const c = orb.style.getPropertyValue('--c');
      orb.style.opacity = active ? '1' : '.6';
      orb.style.transform = active ? 'scale(1.18)' : 'scale(1)';
      orb.style.boxShadow = active ? `0 0 38px 8px ${c}` : `0 0 18px ${c}55`;
    }
    const a = window.COUNCIL_AGENTS.find(x => x.id === agentId);
    document.getElementById('c-who').textContent = a ? a.name : '';
    document.getElementById('c-who').style.color = a ? a.color : '#fff';
    document.getElementById('c-line').textContent = line || '';
  }
  function setReactions(map) {
    const glyph = { agree: '✓', object: '✕', think: '…' };
    const col = { agree: '#7dffb0', object: '#ff9b9b', think: '#9fc4ff' };
    for (const id in nodeEls) {
      const r = nodeEls[id].querySelector('.c-react');
      const v = map[id];
      r.textContent = v ? glyph[v] : '';
      r.style.color = v ? col[v] : 'transparent';
    }
  }
  function setConfidence(pct, frontLabel, deltaText) {
    document.getElementById('c-fill').style.width = pct + '%';
    document.getElementById('c-front').textContent = frontLabel || '';
    document.getElementById('c-delta').textContent = deltaText || '';
  }
  function showChips(chips) {
    document.querySelectorAll('.c-chip').forEach(e => e.remove());
    for (const c of chips) {
      const [x, y] = CouncilMap.projectToScreen(c.lon, c.lat);
      const chip = el('div', 'c-chip', c.text);
      chip.style.cssText = `position:absolute;left:${x}px;top:${y}px;transform:translate(-50%,-140%);font-size:10px;padding:4px 9px;border-radius:12px;white-space:nowrap;background:rgba(14,28,48,.9);border:1px solid ${c.danger ? '#6e2c2c' : '#1e3a5c'};color:${c.danger ? '#ffb3b3' : '#bcd4f0'}`;
      hud.appendChild(chip);
    }
  }
  function attackBeam(fromAgentId, lon, lat) {
    document.querySelectorAll('.c-beam').forEach(e => e.remove());
    const node = nodeEls[fromAgentId]; if (!node) return;
    const nr = node.getBoundingClientRect();
    const [tx, ty] = CouncilMap.projectToScreen(lon, lat);
    const x1 = nr.left + nr.width / 2, y1 = nr.top + 30;
    const len = Math.hypot(tx - x1, ty - y1), ang = Math.atan2(ty - y1, tx - x1) * 180 / Math.PI;
    const beam = el('div', 'c-beam');
    beam.style.cssText = `position:absolute;left:${x1}px;top:${y1}px;height:3px;width:${len}px;transform-origin:left center;transform:rotate(${ang}deg);background:linear-gradient(90deg,#ff5a5a,rgba(255,120,120,.15));box-shadow:0 0 12px 2px rgba(255,80,80,.5)`;
    hud.appendChild(beam);
    setTimeout(() => beam.remove(), 2500);
  }
  function clearTransient() { document.querySelectorAll('.c-chip,.c-beam').forEach(e => e.remove()); }

  return { mount, setPhase, setActiveSpeaker, setReactions, setConfidence, showChips, attackBeam, clearTransient };
})();
```

- [ ] **Step 2: Temporarily call `CouncilUI.mount()` to verify rendering**

In `council.html`, change the boot script to:
```javascript
CouncilMap.initMap();
CouncilUI.mount();
CouncilUI.setPhase('ROUND 3 · CROSS-EXAMINATION');
CouncilUI.setActiveSpeaker('devil', 'Before we celebrate — its weakest dimension is growth.');
CouncilUI.setReactions({ risk: 'agree', market: 'think', community: 'object' });
CouncilUI.setConfidence(61, 'Buckeye West', '▼ 78% → 61% (challenged)');
```

- [ ] **Step 3: Verify in the preview**

`preview_start` → `http://localhost:8077/council.html`, `preview_screenshot`.
**Expected to observe:** six agent nodes around the map (Devil's Advocate lower-center, red), the Devil enlarged/lit, reaction badges on three teammates, the confidence meter at ~61% reading "Buckeye West", a lower-third caption with the Devil's line, and the redirect bar across the bottom. It should resemble the locked mockup.

- [ ] **Step 4: Revert the temporary boot block** back to:
```javascript
CouncilMap.initMap();
// Director.start() wired in Task 11.
```

- [ ] **Step 5: Commit**

```bash
git add council/ui.js council.html
git commit -m "feat(council): council-of-light HUD (nodes, spotlight, meter, caption, beam)"
```

---

## Task 10: Map overlays wired to engine zones (verify in browser)

The overlay layers were defined in Task 8's `map.js`. This task verifies they render correctly from real engine output, before the director drives them.

**Files:**
- (verification only; no new files unless a bug is found in `council/map.js`)

- [ ] **Step 1: Temporary boot block to drive overlays**

In `council.html` boot script, temporarily:
```javascript
CouncilMap.initMap();
const data = { tracts: window.TRACTS, branches: window.BRANCH_DATA.branches,
  craTract: window.CRA_TRACT, income: window.INCOME_DATA };
const zones = CouncilEngine.normalizeZones(CouncilEngine.deriveSignals(CouncilEngine.buildZones(data)));
CouncilMap.setZones(zones);
CouncilMap.setOverlay('community', true);
```

- [ ] **Step 2: Verify in the preview**

`preview_start` → `http://localhost:8077/council.html`, `preview_screenshot`.
**Expected:** a green community-need heat cloud over the tracts, brightest in low-income/low-lending areas; towers still visible. Edit the boot line to `'gap'`/`'saturation'` and re-screenshot — colors change (blue / amber).
Check `preview_console_logs` — **Expected:** no errors (esp. none from `buildZones` over the real ~1196 tracts × 1668 branches; it should complete in well under ~1s).

- [ ] **Step 3: Revert the temporary boot block** to:
```javascript
CouncilMap.initMap();
// Director.start() wired in Task 11.
```

- [ ] **Step 4: Commit (only if a fix was needed)**

```bash
git add council/map.js
git commit -m "fix(council): map overlays render correctly from engine zones"
```
If no fix was needed, skip the commit and note "Task 10 verified, no changes."

---

## Task 11: Director — choreography, controls, interrupt (`council/director.js`)

Wire engine + map + ui + script into the 5-beat show with presenter controls and live redirect. Browser-verified end to end.

**Files:**
- Modify: `branchscape/council/director.js`
- Modify: `branchscape/council.html` (boot `Director.start()`)

- [ ] **Step 1: Implement the director**

```javascript
// branchscape/council/director.js  (browser-only)
const Director = (function () {
  const BEATS = ['mandate', 'gather', 'positions', 'crossExam', 'verdict'];
  const PHASE_LABEL = {
    mandate: 'BEAT 1 · THE MANDATE', gather: 'BEAT 2 · GATHERING DATA',
    positions: 'BEAT 3 · OPENING POSITIONS', crossExam: 'BEAT 4 · CROSS-EXAMINATION',
    verdict: 'BEAT 5 · THE VOTE',
  };
  const SPEAK_MS = 3200;
  let mandate, ranked, challenge, confBefore, beatIdx = 0, lineIdx = 0, playing = false, timer = null;

  const data = () => ({ tracts: window.TRACTS, branches: window.BRANCH_DATA.branches,
    craTract: window.CRA_TRACT, income: window.INCOME_DATA });
  const labelFor = z => 'tract ' + z.geoid.slice(-4); // human-ish label; Phase 3 maps to place names

  function recompute(text) {
    mandate = window.CouncilMandate.parseMandate(text);
    const zones = window.CouncilEngine.normalizeZones(
      window.CouncilEngine.deriveSignals(window.CouncilEngine.buildZones(data())));
    ranked = window.CouncilEngine.rankZones(zones, mandate.weights);
    challenge = window.CouncilEngine.devilsChallenge(ranked, mandate.weights);
    confBefore = window.CouncilEngine.computeConfidence(ranked, window.COUNCIL_AGENTS);
    CouncilMap.setZones(ranked);
    CouncilMap.dropPins(ranked.slice(0, 3));
  }
  function fill(text) {
    const front = labelFor(ranked[0]), runner = labelFor(ranked[1] || ranked[0]);
    return text.replace(/{front}/g, front).replace(/{runner}/g, runner)
      .replace(/{conf}/g, confBefore).replace(/{dim}/g, challenge.dimension);
  }

  function applyBeatVisuals(beat) {
    CouncilUI.setPhase(PHASE_LABEL[beat]);
    if (beat === 'gather') {
      CouncilMap.setOverlay('gap', true); CouncilMap.setOverlay('saturation', true); CouncilMap.setOverlay('community', true);
      CouncilUI.showChips([
        { lon: ranked[0].lon, lat: ranked[0].lat, text: 'widest deposit gap' },
        { lon: ranked[0].lon, lat: ranked[0].lat, text: 'CRA-eligible' },
      ]);
    }
    if (beat === 'positions') {
      CouncilUI.setConfidence(confBefore, labelFor(ranked[0]), '');
    }
    if (beat === 'crossExam') {
      const after = window.CouncilEngine.applyChallenge(ranked, challenge);
      const confAfter = window.CouncilEngine.computeConfidence(after, window.COUNCIL_AGENTS);
      CouncilUI.attackBeam('devil', ranked[0].lon, ranked[0].lat);
      CouncilUI.setConfidence(confAfter, labelFor(ranked[0]), `▼ ${confBefore}% → ${confAfter}%  (challenged)`);
      CouncilUI.setReactions({ risk: 'agree', market: 'think', community: 'object', realestate: 'think' });
    }
    if (beat === 'verdict') {
      const votes = window.CouncilEngine.computeVotes(ranked[0], window.COUNCIL_AGENTS);
      const react = {}; for (const v of votes) react[v.id] = v.vote === 'no' ? 'object' : 'agree';
      CouncilUI.setReactions(react);
    }
  }

  function playLine() {
    const beat = BEATS[beatIdx];
    const lines = window.COUNCIL_SCRIPT.beats[beat];
    if (lineIdx === 0) applyBeatVisuals(beat);
    if (lineIdx >= lines.length) { return nextBeat(); }
    const ln = lines[lineIdx++];
    CouncilUI.setActiveSpeaker(ln.agent, fill(ln.text));
    if (playing) timer = setTimeout(playLine, SPEAK_MS);
  }
  function nextBeat() {
    if (beatIdx < BEATS.length - 1) { beatIdx++; lineIdx = 0; playLine(); }
    else { playing = false; }
  }

  function start(text) { recompute(text || ''); beatIdx = 0; lineIdx = 0; playing = true; CouncilUI.mount(); playLine(); }
  function play() { if (!playing) { playing = true; playLine(); } }
  function pause() { playing = false; clearTimeout(timer); }
  function step() { pause(); playLine(); }
  function redirect(text) { // interrupt: re-pose/steer, re-deliberate from cross-exam
    pause(); recompute(text); beatIdx = BEATS.indexOf('crossExam'); lineIdx = 0; CouncilUI.clearTransient();
    playing = true; CouncilUI.setActiveSpeaker('chair', 'New direction from the room — re-running the numbers…');
    setTimeout(playLine, 1400);
  }

  function wireControls() {
    document.addEventListener('keydown', e => {
      if (e.target && e.target.id === 'c-input') return;
      if (e.code === 'Space') { e.preventDefault(); playing ? pause() : play(); }
      if (e.code === 'ArrowRight') { e.preventDefault(); step(); }
    });
    const send = () => { const v = document.getElementById('c-input').value.trim(); if (v) { redirect(v); document.getElementById('c-input').value = ''; } };
    document.getElementById('c-send').addEventListener('click', send);
    document.getElementById('c-input').addEventListener('keydown', e => { if (e.code === 'Enter') send(); });
  }
  return { start, play, pause, step, redirect, wireControls };
})();
```

- [ ] **Step 2: Boot the director in `council.html`**

Replace the boot script with:
```javascript
CouncilMap.initMap();
CouncilUI.mount();
Director.wireControls();
Director.start('Open one new branch in Maricopa — balance deposit growth with community access');
```

- [ ] **Step 3: Verify the full show in the preview**

`preview_start` → `http://localhost:8077/council.html`.
- `preview_screenshot` immediately, then use `preview_eval` to drive: `Director.pause()` then `Director.step()` repeatedly, screenshotting each beat.
**Expected to observe across beats:** Beat 1 chair states the mandate; Beat 2 the three heat overlays bloom + chips appear, each specialist speaks in turn (spotlight moves); Beat 3 confidence meter shows a value; Beat 4 the red attack-beam fires from the Devil to the front-runner and **the meter visibly drops**, reactions update; Beat 5 votes light up and the chair announces the recommendation with the caveat.
- Test interrupt: `preview_fill` the `#c-input` with "prioritize underbanked communities" → `preview_click` `#c-send` → `preview_screenshot`. **Expected:** the chair says it's re-running, overlays/pins update, and the front-runner label may change.
- `preview_console_logs` — **Expected:** no errors.

- [ ] **Step 4: Verify offline end-to-end**

`preview_start` → `http://localhost:8077/council.html?offline`, drive the same steps. **Expected:** identical behavior on the black void, zero network requests (`preview_network` shows no tile/API calls).

- [ ] **Step 5: Commit**

```bash
git add council/director.js council.html
git commit -m "feat(council): 5-beat director, presenter controls, live redirect"
```

---

## Task 12: Integration smoke test + README + venue polish

**Files:**
- Create: `branchscape/council/integration.test.js`
- Modify: `branchscape/README.md`

- [ ] **Step 1: Write an integration smoke test over the REAL data**

```javascript
// branchscape/council/integration.test.js
const test = require('node:test');
const assert = require('node:assert');
global.window = {};
require('../data/branches.js'); require('../data/cra_tract.js');
require('../data/income.js'); require('../data/tracts.js');
const E = require('./engine.js');
const M = require('./mandate.js');
const AGENTS = require('./agents.js');

test('full pipeline produces a sane ranking over real Maricopa data', () => {
  const data = { tracts: window.TRACTS, branches: window.BRANCH_DATA.branches,
    craTract: window.CRA_TRACT, income: window.INCOME_DATA };
  const m = M.parseMandate('balance deposit growth with community access');
  const ranked = E.rankZones(E.normalizeZones(E.deriveSignals(E.buildZones(data))), m.weights);
  assert.ok(ranked.length > 100);                       // ~1196 tracts
  assert.ok(ranked[0].score >= ranked[ranked.length - 1].score);
  const conf = E.computeConfidence(ranked, AGENTS);
  assert.ok(conf >= 0 && conf <= 100);
  const ch = E.devilsChallenge(ranked, m.weights);
  assert.ok(E.applyChallenge(ranked, ch)[0] !== undefined);
});
```

- [ ] **Step 2: Run the full suite**

Run: `node --test council/`
Expected: PASS (all suites: agents, engine, mandate, script, integration).

- [ ] **Step 3: Add a README section**

Append to `branchscape/README.md`:
```markdown
## THE COUNCIL (Act 2) — multi-agent branch-siting demo

Open `council.html` (same server as BRANCHSCAPE). Six AI agents deliberate over the
Maricopa map to decide where to open the next branch.

- **Run:** `python3 -m http.server 8000` → open `http://localhost:8000/council.html`
  (append `?offline` for the zero-network void — recommended for the venue).
- **Presenter controls:** **Space** play/pause · **→** step one line · type in the
  bottom bar and hit **Enter / Redirect** to re-pose the question or steer the council
  (e.g. "prioritize underbanked communities", "consider a rural town").
- **Tests:** `node --test council/` (zero dependencies).
- **What's real vs modeled:** deposit gap, saturation, and community/CRA need come from
  FDIC SOD + FFIEC CRA + IRS income; **growth and cost are modeled proxies** and are
  labeled as such. The Devil's Advocate attacks a real weak signal of the front-runner.
- Phase 2 (live agent voices) and Phase 3 (analog metros) are separate, later additions.
```

- [ ] **Step 4: Final full-run rehearsal verification**

Serve and `preview_start` → `http://localhost:8077/council.html?offline`. Run the entire show start→finish using only Space/→, then do one redirect. **Expected:** a clean ~4–6 min run with no stalls, no console errors, the meter moving at cross-exam, and a coherent verdict. Capture a final `preview_screenshot` of the verdict beat as evidence.

- [ ] **Step 5: Commit**

```bash
git add council/integration.test.js README.md
git commit -m "test(council): real-data integration smoke + README + venue notes"
```

---

## Self-Review (completed against the spec)

- **Spec §5 Hybrid architecture** → engine is deterministic/offline (Tasks 2–5); static script always present (Task 7); live voices are explicitly Phase 2 (out of this plan). ✔
- **Spec §6 Six agents** → Task 1 roster; owned signals used in votes (Task 4) and reactions (Task 11). ✔
- **Spec §7 Decision engine** (signals, winsorized scoring, confidence, votes, DA counter-signal) → Tasks 2–5. ✔
- **Spec §8 Data reuse + honesty labels** → real globals reused (Tasks 8/10/12); `modeled:['growth','cost']` carried through; README "real vs modeled". ✔
- **Spec §9 Council-of-Light visual** (spotlight, reaction badges, meter, chips, attack-beam, caption, redirect bar) → Task 9. ✔
- **Spec §10 Five-beat choreography** → Task 11 BEATS + applyBeatVisuals. ✔
- **Spec §11 Presenter-driven anytime interrupt** → Task 11 `redirect()` + key/`#c-input` controls. ✔
- **Spec §13 Reliability/offline** → `?offline` verified in Tasks 8 and 11; no-CDN reuse of vendored libs; deterministic core. ✔
- **Type consistency:** signal keys (`depositGap/growth/communityNeed/saturation/cost`), beat ids (`mandate/gather/positions/crossExam/verdict`), and namespaces (`CouncilEngine/COUNCIL_AGENTS/CouncilMandate/COUNCIL_SCRIPT/CouncilMap/CouncilUI/Director`) are identical across all tasks. ✔
- **Placeholder scan:** every code step contains complete code; the script content is fully written. Map/ui/director are verified via preview with explicit expected observations (no DOM unit framework invented). ✔
- **Out of scope (correctly deferred to separate plans):** live `/voice` helper (Phase 2), analog metros + place-name labels (Phase 3). `labelFor()` uses tract suffixes in Phase 1 — a deliberate, documented stand-in until Phase 3 adds place names.

## Future phases (separate plans, only after Phase 1 is solid)
- **Phase 2 — Live Voices:** `council_server.py` serving the folder + `POST /voice` (agent, role, mandate, signals, state) → Claude, key in server env only; `director.js` gains an async voice provider that races a short timeout and falls back to `COUNCIL_SCRIPT`.
- **Phase 3 — Analog Metros:** re-run `fetch_*.py` for 3–5 county FIPS; per-metro data globals + scenario config + place-name labels; a metro switcher in the redirect bar.
