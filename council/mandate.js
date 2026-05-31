// branchscape/council/mandate.js
(function (global) {
  function parseMandate(text) {
    const t = (text || '').toLowerCase();
    const weights = { depositGap: 1, growth: 1, communityNeed: 1, saturation: 1, cost: 0.5 };
    const flags = [];
    if (/communit|underbank|access|cra|lmi|equit/.test(t)) weights.communityNeed += 1.5;
    if (/deposit|growth|profit|return|aggress/.test(t)) { weights.depositGap += 1; weights.growth += 0.5; }
    if (/competition|saturat|cannibal/.test(t)) weights.saturation += 1;
    if (/cost|cheap|budget|lease|rent/.test(t)) weights.cost += 1;
    if (/rural|small town|outlying/.test(t)) { flags.push('rural'); weights.saturation += 0.5; }
    const label = (text && text.trim()) ||
      'Open one new branch in Maricopa — balance deposit growth with community access';
    return { weights, label, flags };
  }
  const Mandate = { parseMandate };
  if (typeof module !== 'undefined' && module.exports) module.exports = Mandate;
  else global.CouncilMandate = Mandate;
})(typeof window !== 'undefined' ? window : globalThis);
