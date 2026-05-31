// branchscape/council/agents.js
(function (global) {
  const COUNCIL_AGENTS = [
    { id: 'chair',      name: 'Chair / President',      icon: '⚖️', color: '#bfe3ff', role: 'synthesizes · calls the vote', signal: 'composite', threshold: null },
    { id: 'market',     name: 'Market Analyst',         icon: '📈', color: '#7fd3ff', role: 'deposit gaps · growth',        signal: 'depositGap',  threshold: 0.5 },
    { id: 'risk',       name: 'Risk Officer',           icon: '🛡️', color: '#ffb86b', role: 'competition · saturation',     signal: 'saturation',  threshold: 0.5, invert: true },
    { id: 'community',  name: 'Community / CRA Officer', icon: '🤝', color: '#6ad6b0', role: 'underbanked access',           signal: 'communityNeed', threshold: 0.5 },
    { id: 'realestate', name: 'Real-Estate Scout',      icon: '💵', color: '#c89bff', role: 'sites · cost · feasibility',   signal: 'cost',        threshold: 0.5, invert: true },
    { id: 'devil',      name: "Devil's Advocate",       icon: '😈', color: '#ff5a5a', role: 'challenges the front-runner',  signal: 'counter',     threshold: null },
  ];
  if (typeof module !== 'undefined' && module.exports) module.exports = COUNCIL_AGENTS;
  else global.COUNCIL_AGENTS = COUNCIL_AGENTS;
})(typeof window !== 'undefined' ? window : globalThis);
