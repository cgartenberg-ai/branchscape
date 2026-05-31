// branchscape/council/integration.test.js
// End-to-end over the REAL Maricopa data globals (not a fixture).
const assert = require('node:assert');
const { test, report } = require('./_harness.js');
global.window = {};
require('../data/branches.js');
require('../data/cra_tract.js');
require('../data/income.js');
require('../data/tracts.js');
const E = require('./engine.js');
const M = require('./mandate.js');
const AGENTS = require('./agents.js');

const data = () => ({
  tracts: window.TRACTS,
  branches: window.BRANCH_DATA.branches,
  craTract: window.CRA_TRACT,
  income: window.INCOME_DATA,
});

test('full pipeline produces a sane ranking over real Maricopa data', () => {
  const m = M.parseMandate('balance deposit growth with community access');
  const ranked = E.rankZones(E.normalizeZones(E.deriveSignals(E.buildZones(data()))), m.weights);
  assert.ok(ranked.length > 100, `expected >100 tracts, got ${ranked.length}`);
  for (let i = 1; i < ranked.length; i++) assert.ok(ranked[i - 1].score >= ranked[i].score);
  const conf = E.computeConfidence(ranked, AGENTS);
  assert.ok(conf >= 0 && conf <= 100);
  const ch = E.devilsChallenge(ranked, m.weights);
  assert.ok(E.applyChallenge(ranked, ch)[0] !== undefined);
});

test('a community-first mandate changes the front-runner vs the balanced one', () => {
  const zones = E.normalizeZones(E.deriveSignals(E.buildZones(data())));
  const balanced = E.rankZones(zones, M.parseMandate('balance deposit growth with community access').weights);
  const community = E.rankZones(zones, M.parseMandate('prioritize underbanked communities over deposit growth').weights);
  assert.notStrictEqual(balanced[0].geoid, community[0].geoid);
});

test('the devil\'s challenge lowers post-challenge confidence on real data', () => {
  const m = M.parseMandate('balance deposit growth with community access');
  const ranked = E.rankZones(E.normalizeZones(E.deriveSignals(E.buildZones(data()))), m.weights);
  const before = E.computeConfidence(ranked, AGENTS);
  const after = E.computeConfidence(E.applyChallenge(ranked, E.devilsChallenge(ranked, m.weights)), AGENTS);
  assert.ok(after <= before, `expected post-challenge ${after} <= pre ${before}`);
});

report();
