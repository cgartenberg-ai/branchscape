// branchscape/council/script.test.js
const assert = require('node:assert');
const { test, report } = require('./_harness.js');
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

report();
