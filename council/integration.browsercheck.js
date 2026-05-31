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

  const community = E.rankZones(zones, M.parseMandate('prioritize underbanked communities over deposit growth').weights);
  checks.push(['community mandate changes the front-runner', balanced[0].geoid !== community[0].geoid]);

  const ch = E.devilsChallenge(balanced, M.parseMandate('balance deposit growth with community access').weights);
  const after = E.computeConfidence(E.applyChallenge(balanced, ch), A);
  checks.push(['devil\'s challenge lowers post-challenge confidence', after <= conf]);

  const pass = checks.every(c => c[1]);
  return { pass, results: checks.map(c => ({ name: c[0], ok: c[1] })) };
}
if (typeof window !== 'undefined') window.runCouncilChecks = runCouncilChecks;
