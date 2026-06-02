// branchscape/council/setup.js  (browser-only)
// Presenter setup panel for THE COUNCIL (live): pick a bank archetype (or customize the
// fields), then "Convene the council". Builds a `profile` object + mandate and hands them
// to onConvene(mandate, profile) — which fires the live deliberation. The agents then
// reason AS that specific bank (profile threads into every agent's system prompt server-side).
const CouncilSetup = (function () {
  // Three seeded, realistic ABA archetypes. Edit freely — these are just starting points.
  const ARCHETYPES = [
    { key: 'community', label: 'Community Bank',
      name: 'Cactus Community Bank', type: 'community', asset_size: '$850M',
      region: 'East Valley (Mesa, Tempe, Chandler)',
      values: ['local relationships', 'small-business lending', 'CRA leadership'],
      mandate: 'Open one new branch that deepens our community roots and CRA standing while still growing core deposits.' },
    { key: 'rural', label: 'Rural / Ag Bank',
      name: 'Sonoran Ag & Trust', type: 'rural agricultural', asset_size: '$420M',
      region: 'West Valley & outlying Maricopa (Buckeye, Gila Bend)',
      values: ['agricultural lending', 'long-horizon customer loyalty', 'serving thin markets'],
      mandate: 'Open one new branch that reaches underbanked outlying communities without overextending into saturated metro corridors.' },
    { key: 'commercial', label: 'Commercial Bank',
      name: 'Phoenix Meridian Bank', type: 'mid-size commercial', asset_size: '$6.5B',
      region: 'Greater Phoenix metro',
      values: ['commercial & CRE lending', 'treasury services', 'scale and efficiency'],
      mandate: 'Open one new branch that maximizes deposit growth and commercial relationships with strong risk-adjusted returns.' },
  ];

  const FIELDS = [
    { id: 'name', label: 'Bank name', ph: 'e.g. Cactus Community Bank' },
    { id: 'type', label: 'Type', ph: 'e.g. community / rural / commercial' },
    { id: 'asset_size', label: 'Asset size', ph: 'e.g. $850M' },
    { id: 'region', label: 'Region / footprint', ph: 'e.g. East Valley (Mesa, Tempe)' },
    { id: 'values', label: 'Values / priorities (comma-separated)', ph: 'e.g. CRA leadership, small-business lending' },
  ];

  function $(id) { return document.getElementById(id); }

  function fill(a) {
    $('cs-name').value = a.name;
    $('cs-type').value = a.type;
    $('cs-asset_size').value = a.asset_size;
    $('cs-region').value = a.region;
    $('cs-values').value = a.values.join(', ');
    $('cs-mandate').value = a.mandate;
  }

  function readProfile() {
    const values = $('cs-values').value.split(',').map(s => s.trim()).filter(Boolean);
    return {
      name: $('cs-name').value.trim(),
      type: $('cs-type').value.trim(),
      asset_size: $('cs-asset_size').value.trim(),
      region: $('cs-region').value.trim(),
      values: values,
    };
  }

  // onConvene(mandate, profile) -> void. Renders the panel; removes it on convene.
  function mount(onConvene) {
    const old = $('council-setup'); if (old) old.remove();
    const overlay = document.createElement('div');
    overlay.id = 'council-setup';
    overlay.style.cssText = 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;' +
      'background:radial-gradient(ellipse at center,rgba(4,10,22,.62),rgba(2,4,10,.9));pointer-events:auto;z-index:40';

    const inputCss = 'width:100%;box-sizing:border-box;margin-top:4px;background:rgba(6,14,26,.9);border:1px solid #1e3a5c;' +
      'border-radius:7px;color:#e8f1ff;font-size:13px;padding:8px 10px;outline:none;font-family:inherit';
    const fieldRows = FIELDS.map(f =>
      `<label style="display:block;margin-top:11px;font-size:10.5px;letter-spacing:1px;color:#7f99b8;text-transform:uppercase">${f.label}` +
      `<input id="cs-${f.id}" placeholder="${f.ph}" style="${inputCss}"></label>`).join('');
    const presetBtns = ARCHETYPES.map(a =>
      `<div class="cs-preset" data-key="${a.key}" style="flex:1;cursor:pointer;text-align:center;padding:11px 8px;border-radius:9px;` +
      `background:linear-gradient(180deg,rgba(20,40,66,.9),rgba(14,28,48,.9));border:1px solid #244a70;transition:.18s">` +
      `<div style="font-size:13px;font-weight:600;color:#cfe0f5">${a.label}</div>` +
      `<div style="font-size:10px;color:#7f99b8;margin-top:3px">${a.asset_size} · ${a.type}</div></div>`).join('');

    const card = document.createElement('div');
    card.style.cssText = 'width:560px;max-width:92vw;max-height:90vh;overflow:auto;background:linear-gradient(180deg,rgba(10,20,36,.97),rgba(8,16,30,.98));' +
      'border:1px solid #1e3a5c;border-radius:16px;padding:26px 30px;box-shadow:0 0 60px rgba(10,40,90,.45)';
    card.innerHTML =
      '<div style="font-size:10px;letter-spacing:5px;color:#5b7290;text-transform:uppercase">BRANCHSCAPE · ACT 2 — THE COUNCIL</div>' +
      '<div style="font-size:23px;font-weight:600;color:#eaf2ff;margin-top:7px">Convene the council</div>' +
      '<div style="font-size:12.5px;color:#8aa0bb;margin-top:6px;line-height:1.5">Choose a bank archetype or enter your own. The six AI specialists will reason and argue <i>as your bank</i> over real Maricopa County data.</div>' +
      `<div style="display:flex;gap:10px;margin-top:18px">${presetBtns}</div>` +
      fieldRows +
      '<label style="display:block;margin-top:11px;font-size:10.5px;letter-spacing:1px;color:#7f99b8;text-transform:uppercase">Mandate (the question to deliberate)' +
      `<textarea id="cs-mandate" rows="3" placeholder="e.g. Open one new branch that balances deposit growth with community access." style="${inputCss};resize:vertical;line-height:1.45"></textarea></label>` +
      '<div id="cs-go" style="margin-top:20px;background:linear-gradient(90deg,#1c66ff,#3b86ff);color:#fff;font-size:14px;font-weight:600;' +
      'text-align:center;padding:13px;border-radius:10px;cursor:pointer;box-shadow:0 0 24px rgba(40,110,255,.4)">Convene the council ▸</div>' +
      '<div id="cs-hint" style="font-size:11px;color:#6f88a6;text-align:center;margin-top:9px;min-height:14px"></div>';
    overlay.appendChild(card);
    (document.getElementById('hud') || document.body).appendChild(overlay);

    card.querySelectorAll('.cs-preset').forEach(btn => {
      btn.addEventListener('click', () => {
        const a = ARCHETYPES.find(x => x.key === btn.getAttribute('data-key'));
        fill(a);
        card.querySelectorAll('.cs-preset').forEach(b => b.style.borderColor = '#244a70');
        btn.style.borderColor = '#3b86ff';
      });
    });
    fill(ARCHETYPES[0]);                                  // sensible default
    card.querySelector('.cs-preset').style.borderColor = '#3b86ff';

    $('cs-go').addEventListener('click', () => {
      const mandate = $('cs-mandate').value.trim();
      if (!mandate) { $('cs-hint').textContent = 'Enter a mandate to convene.'; return; }
      const profile = readProfile();
      overlay.remove();
      onConvene(mandate, profile);
    });
  }

  const api = { mount, ARCHETYPES };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else if (typeof window !== 'undefined') window.CouncilSetup = api;
  return api;
})();
