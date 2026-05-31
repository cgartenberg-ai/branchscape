// branchscape/council/integration.browsercheck.js
// Real-data end-to-end checks, run IN THE BROWSER (not node).
//
// Why browser, not `node --test`: on this machine node segfaults *mid-require*
// while loading the ~1 MB data/branches.js (the durable result file is never
// written — reproduced 5/5 times), so a node integration test can't run here.
// The browser loads the data globals fine (it's the real runtime), so the
// real-data pipeline is verified here instead. Call runCouncilChecks() from the
// console or via the preview tooling; returns { pass, results: [{name, ok}] }.

function runCouncilChecks() {
  const E = window.CouncilEngine, M = window.CouncilMandate, A = window.COUNCIL_AGENTS;
  const data = {
    tracts: window.TRACTS, branches: window.BRANCH_DATA.branches,
    craTract: window.CRA_TRACT, income: window.INCOME_DATA,
  };
  const zones = E.normalizeZones(E.deriveSignals(E.buildZones(data)));
  const checks = [];

  const balanced = E.rankZones(zones, M.parseMandate('balance deposit growth with community access').weights);
  checks.push(['>100 tracts ranked', balanced.length > 100]);

  let sorted = true;
  for (let i = 1; i < balanced.length; i++) if (balanced[i - 1].score < balanced[i].score) sorted = false;
  checks.push(['ranking sorted descending', sorted]);

  const conf = E.computeConfidence(balanced, A);
  checks.push(['confidence within 0..100', conf >= 0 && conf <= 100]);

  // Contrasting mandates must pick different winners. Use phrases with DISJOINT
  // keywords (the old pair both said "deposit growth" AND "community" -> same weights).
  const profit = E.rankZones(zones, M.parseMandate('maximize deposit growth and profit in the wealthiest markets').weights);
  const mission = E.rankZones(zones, M.parseMandate('prioritize underbanked low-income communities and CRA access').weights);
  checks.push(['contrasting mandates pick different winners', profit[0].geoid !== mission[0].geoid]);

  // The Devil's challenge must lower confidence OF THE NAMED RECOMMENDATION (anchored
  // to one geoid), not of whatever ends up at #1 after the penalty.
  const rec = balanced[0].geoid;
  const wch = M.parseMandate('balance deposit growth with community access').weights;
  const ch = E.devilsChallenge(balanced, wch);
  const cBefore = E.confidenceOfPick(balanced, rec, A);
  const cAfter = E.confidenceOfPick(E.applyChallenge(balanced, ch), rec, A);
  checks.push(['devil\'s challenge lowers the recommendation\'s confidence', cAfter < cBefore]);

  const pass = checks.every(c => c[1]);
  return { pass, results: checks.map(c => ({ name: c[0], ok: c[1] })) };
}
if (typeof window !== 'undefined') window.runCouncilChecks = runCouncilChecks;
