// branchscape/council/engine.js
// Deterministic decision engine for THE COUNCIL. Pure functions, dual-mode
// (module.exports in Node, window.CouncilEngine in the browser). No DOM, no network.
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
  function median(values) {
    const s = [...values].sort((a, b) => a - b);
    return s.length ? s[Math.floor(s.length / 2)] : 0;
  }

  // data = { tracts:{geoid:[lon,lat]}, branches:[{lat,lon,dep:{year}}],
  //          craTract:{tracts:{geoid:{amt,n}}}, income:[{lat,lon,income}] }
  function buildZones(data, opts = {}) {
    const radiusKm = opts.radiusKm || 3;
    const latestYear = opts.latestYear || '2024';
    const baseYear = opts.baseYear || '2015';
    const zones = [];
    for (const geoid of Object.keys(data.tracts)) {
      // Skip Census "special" tracts (9800-9999 = water, parks, airports, other
      // non-residential). With no residents they get ~zero deposits/CRA and a nearest
      // high-income ZIP, so they pin every winsorized signal to 1 and dominate the
      // ranking regardless of mandate. They are not real branch sites.
      if (parseInt(geoid.slice(-6), 10) >= 980000) continue;
      const [lon, lat] = data.tracts[geoid];
      let saturation = 0, capturedDeposits = 0, capturedBase = 0;
      for (const b of data.branches) {
        if (haversineKm(lat, lon, b.lat, b.lon) <= radiusKm) {
          saturation++;
          capturedDeposits += num(b.dep && b.dep[latestYear]);
          capturedBase += num(b.dep && b.dep[baseYear]);
        }
      }
      // nearest income point (ZIP AGI proxy for demand/spending power)
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

  // Derived signals. depositGap & communityNeed are grounded in real data; growth
  // & cost are modeled proxies (flagged in `modeled`).
  //
  // depositGap = DEMAND (income) x UNDER-CAPTURE. Under-capture is a bounded ratio
  // (→1 for a zone with no nearby deposits, →0 as deposits grow), so depositGap rises
  // with spending power AND with how little of it local branches capture. Crucially it
  // rises with income, while communityNeed rises as income FALLS — so a deposit-growth
  // mandate and a community-access mandate pull toward different zones (the demo's
  // profit-vs-mission tension), instead of one near-empty outlier maxing every axis
  // (the old income/(deposits+1) form blew up for tiny-deposit tracts).
  function deriveSignals(zones) {
    const k = 1; // smoothing
    const medianIncome = median(zones.map(z => z.income));
    const medianCapDep = median(zones.map(z => z.capturedDeposits).filter(d => d > 0)) || 1;
    return zones.map(z => {
      const underCapture = 1 - z.capturedDeposits / (z.capturedDeposits + medianCapDep); // 1..~0
      const depositGap = z.income * underCapture;
      const growth = z.capturedDeposits / (z.capturedBase + k);
      const incomeNeed = medianIncome > 0 ? Math.max(0, (medianIncome - z.income) / medianIncome) : 0;
      // Graded lending-gap with a soft knee (~$250k), NOT the old 1/(craAmt+1) which
      // spiked to 1 for EVERY tract with no CRA record — including wealthy ones — so a
      // rich, no-CRA tract maxed communityNeed AND depositGap at once and no mandate
      // could separate them (RC2). communityNeed now LEADS with low income, so it
      // genuinely opposes depositGap (which rises with income) → mandates diverge.
      const craNeed = 250 / (250 + z.craAmt);
      const communityNeed = 0.75 * incomeNeed + 0.25 * craNeed;
      const cost = z.income; // modeled: higher-income areas cost more to enter
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

  const DEFAULT_WEIGHTS = { depositGap: 1, growth: 1, communityNeed: 1, saturation: 1, cost: 0.5 };
  // Positive signals add; saturation & cost subtract (negatives).
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
    const eff = agent.invert ? (1 - v) : v; // inverted: low saturation/cost is "good"
    if (eff >= agent.threshold) return 'yes';
    if (eff >= agent.threshold - 0.2) return 'conditional';
    return 'no';
  }
  function computeVotes(frontRunner, agents) {
    return agents
      .filter(a => a.threshold !== null)
      .map(a => ({ id: a.id, vote: agentSatisfied(frontRunner, a) }));
  }
  // Confidence = how much the front-runner stands out from the field (#1 vs #2,
  // scaled by the score RANGE so it is stable), plus agent agreement. Because the
  // margin is measured against the field range, penalizing the front-runner's score
  // (the Devil's challenge) always shrinks the gap → confidence drops monotonically,
  // and a challenge that flips the order leaves two bunched leaders → low confidence.
  // (The old code used an unscaled (top-second) margin, so a penalty could reorder
  // the field and paradoxically RAISE the reported number.)
  function computeConfidence(ranked, agents) {
    if (!ranked.length) return 0;
    const top = ranked[0];
    let margin = 0.5;
    if (ranked.length > 1) {
      const hi = ranked[0].score, lo = ranked[ranked.length - 1].score;
      const range = (hi - lo) || 1;
      margin = Math.max(0, Math.min(1, (top.score - ranked[1].score) / range));
    }
    const votes = computeVotes(top, agents);
    const yes = votes.filter(v => v.vote === 'yes').length;
    const agreement = votes.length ? yes / votes.length : 0;
    const pct = 45 + 35 * margin + 20 * agreement;
    return Math.round(Math.max(0, Math.min(100, pct)));
  }
  // The Devil targets the front-runner's weakest real dimension (lowest positive
  // signal, or highest negative like saturation/cost) and returns a grounded penalty.
  function devilsChallenge(ranked, weights) {
    const top = ranked[0];
    const n = top.norm;
    const candidates = [
      { dimension: 'growth',        bad: 1 - n.growth },
      { dimension: 'depositGap',    bad: 1 - n.depositGap },
      { dimension: 'communityNeed', bad: 1 - n.communityNeed },
      { dimension: 'saturation',    bad: n.saturation },
      { dimension: 'cost',          bad: n.cost },
    ];
    candidates.sort((a, b) => b.bad - a.bad);
    const worst = candidates[0];
    return { targetGeoid: top.geoid, dimension: worst.dimension, penalty: 0.3 + 0.5 * worst.bad };
  }
  // Re-score with the challenged dimension penalized on the front-runner, then re-rank.
  function applyChallenge(ranked, challenge) {
    return ranked
      .map(z => z.geoid === challenge.targetGeoid
        ? Object.assign({}, z, { score: z.score - challenge.penalty })
        : Object.assign({}, z))
      .sort((a, b) => b.score - a.score);
  }
  // Confidence of a SPECIFIC pick (the council's named recommendation), measured as
  // its margin over the best OTHER zone in the field, scaled by the field range, plus
  // agent agreement. Unlike computeConfidence (which always scores whatever sits at #1),
  // this is anchored to one geoid — so when the Devil penalizes the recommendation its
  // margin over rivals shrinks (and can go negative → 0) and the number DROPS honestly,
  // even if the penalty drops it below a rival. This is what the meter's "▼" reflects.
  function confidenceOfPick(field, geoid, agents) {
    const z = field.find(x => x.geoid === geoid);
    if (!z) return 0;
    const scores = field.map(x => x.score);
    const hi = Math.max.apply(null, scores), lo = Math.min.apply(null, scores);
    const range = (hi - lo) || 1;
    const bestOther = field.filter(x => x.geoid !== geoid)
      .reduce((m, x) => Math.max(m, x.score), -Infinity);
    const margin = Math.max(0, Math.min(1, (z.score - bestOther) / range));
    const votes = computeVotes(z, agents);
    const yes = votes.filter(v => v.vote === 'yes').length;
    const agreement = votes.length ? yes / votes.length : 0;
    return Math.round(Math.max(0, Math.min(100, 45 + 35 * margin + 20 * agreement)));
  }

  const Engine = {
    haversineKm, median, buildZones, deriveSignals, normalizeZones,
    rankZones, scoreZone, computeVotes, computeConfidence, confidenceOfPick, DEFAULT_WEIGHTS,
    devilsChallenge, applyChallenge,
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = Engine;
  else global.CouncilEngine = Engine;
})(typeof window !== 'undefined' ? window : globalThis);
