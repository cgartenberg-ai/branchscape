// branchscape/council/engine.test.js
const assert = require('node:assert');
const { test, report } = require('./_harness.js');
const E = require('./engine.js');
const AGENTS = require('./agents.js');
const COMMUNITY_WEIGHTS = { depositGap: 1, growth: 0.5, communityNeed: 2, saturation: 1, cost: 0.5 };
function rankedFix(weights) {
  return E.rankZones(E.normalizeZones(E.deriveSignals(E.buildZones(FIX, { radiusKm: 3 }))), weights);
}

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

test('rankZones sorts by weighted score, descending', () => {
  const ranked = rankedFix(COMMUNITY_WEIGHTS);
  for (let i = 1; i < ranked.length; i++) {
    assert.ok(ranked[i - 1].score >= ranked[i].score);
  }
  assert.notStrictEqual(ranked[0].geoid, 'A');
});

test('computeConfidence returns 0..100', () => {
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
  const byId = Object.fromEntries(zones.map(z => [z.geoid, z]));
  assert.ok(byId.C.norm.communityNeed >= byId.A.norm.communityNeed);
  assert.ok(byId.A.norm.saturation >= byId.B.norm.saturation);
});

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

// --- regression tests for the two real-data bugs lost in the first build pass ---

test('D3: a deposit-weighted vs community-weighted mandate pick DIFFERENT zones', () => {
  const zones = E.normalizeZones(E.deriveSignals(E.buildZones(FIX, { radiusKm: 3 })));
  const depositTop = E.rankZones(zones,
    { depositGap: 2, growth: 1, communityNeed: 1, saturation: 1, cost: 0.5 })[0];
  const communityTop = E.rankZones(zones,
    { depositGap: 1, growth: 1, communityNeed: 3, saturation: 1, cost: 0.5 })[0];
  // The mandate must actually move the winner — the old income/(deposits+1) form
  // let one near-empty tract max every axis, so reweighting changed nothing.
  assert.notStrictEqual(depositTop.geoid, communityTop.geoid);
});

test('D4: the devil\'s challenge never RAISES confidence (range-normalized margin)', () => {
  const ranked = rankedFix(COMMUNITY_WEIGHTS);
  const before = E.computeConfidence(ranked, AGENTS);
  const after = E.applyChallenge(ranked, E.devilsChallenge(ranked, COMMUNITY_WEIGHTS));
  const afterConf = E.computeConfidence(after, AGENTS);
  assert.ok(afterConf <= before, `confidence rose after challenge: ${before} -> ${afterConf}`);
});

report();
