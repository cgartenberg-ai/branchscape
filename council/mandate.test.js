// branchscape/council/mandate.test.js
const assert = require('node:assert');
const { test, report } = require('./_harness.js');
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

test('"rural" sets a flag', () => {
  const r = M.parseMandate('consider a rural town');
  assert.ok(r.flags.includes('rural'));
});

report();
