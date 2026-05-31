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
