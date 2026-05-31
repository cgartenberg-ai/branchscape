// branchscape/council/engine.test.js
const assert = require('node:assert');
const { test, report } = require('./_harness.js');
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

report();
