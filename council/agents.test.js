// branchscape/council/agents.test.js
const assert = require('node:assert');
const { test, report } = require('./_harness.js');
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

report();
