// branchscape/council/script.js
(function (global) {
  // {front}=front-runner label, {runner}=runner-up label, {conf}=confidence%,
  // {dim}=challenged dimension. Director substitutes.
  const COUNCIL_SCRIPT = {
    beats: {
      mandate: [
        { agent: 'chair', text: 'Our mandate: open one branch in Maricopa — balance deposit growth with community access. Team, gather your data.' },
      ],
      gather: [
        { agent: 'market',     text: 'Pulling FDIC deposits by tract — mapping where demand outruns the branches that serve it.' },
        { agent: 'risk',       text: 'Overlaying every competitor branch. I want the saturation picture before anyone falls in love with a site.' },
        { agent: 'community',  text: 'Lighting up the underbanked tracts — low small-business lending, below-median income, CRA-eligible.' },
        { agent: 'realestate', text: 'Dropping candidate pins and pricing each — feasibility is where strategy meets the lease.' },
      ],
      positions: [
        { agent: 'market',     text: '{front} has the widest deposit gap in the county — strong households, thin coverage. That\'s my pick.' },
        { agent: 'community',  text: 'Agreed, and {front} is CRA-eligible. Rare alignment of profit and mission — I support it.' },
        { agent: 'realestate', text: 'Site cost at {front} is reasonable; {runner} is cheaper but the demand isn\'t there. I lean {front}.' },
        { agent: 'risk',       text: 'I\'m cautious. Let me stress-test the front-runner before we commit.' },
      ],
      crossExam: [
        { agent: 'devil',  text: 'Before we celebrate {front} — its weakest dimension is {dim}. Your {conf}% confidence is optimistic until we price that in.' },
        { agent: 'risk',   text: 'The Devil\'s right. Discount the win probability — this isn\'t a layup.' },
        { agent: 'market', text: 'Fair. Even discounted, the deposit gap keeps {front} ahead of {runner} — but the margin is narrower now.' },
      ],
      verdict: [
        { agent: 'chair', text: 'I\'m calling the vote.' },
        { agent: 'chair', text: 'The council recommends {front}, at {confFinal}% confidence after the Devil\'s challenge — with the caveat on {dim} noted in the record.' },
      ],
    },
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = COUNCIL_SCRIPT;
  else global.COUNCIL_SCRIPT = COUNCIL_SCRIPT;
})(typeof window !== 'undefined' ? window : globalThis);
