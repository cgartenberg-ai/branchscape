// branchscape/council/ui.js  (browser-only; relies on COUNCIL_AGENTS, CouncilMap)
// The Council-of-Light HUD: six agent nodes around the map, active-speaker
// spotlight, reaction badges, confidence meter, floating data-chips, red attack
// beam, lower-third caption, and the audience redirect bar. Pure presentation —
// it renders state the Director computes; it makes no decisions.
const CouncilUI = (function () {
  const hud = document.getElementById('hud');
  const nodeEls = {};
  // arc positions (% of viewport) keyed by agent id; devil sits low & apart
  const POS = {
    chair: [50, 11], market: [13, 24], realestate: [87, 24],
    risk: [9, 52], community: [91, 52], devil: [50, 73],
  };
  function el(tag, cls, html) { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }

  function mount() {
    hud.innerHTML = '';
    for (const a of window.COUNCIL_AGENTS) {
      const [x, y] = POS[a.id];
      const n = el('div', 'c-node' + (a.id === 'devil' ? ' c-devil' : ''));
      n.style.cssText = `position:absolute;left:${x}%;top:${y}%;transform:translate(-50%,-50%);width:138px;text-align:center;transition:transform .35s,opacity .35s`;
      n.innerHTML =
        `<div class="c-orb" style="--c:${a.color};width:64px;height:64px;border-radius:50%;margin:0 auto;` +
        `display:flex;align-items:center;justify-content:center;font-size:25px;opacity:.62;` +
        `background:radial-gradient(circle at 38% 32%,rgba(40,70,110,.95),rgba(10,20,38,.96));` +
        `border:1.5px solid ${a.color};box-shadow:0 0 18px ${a.color}55;position:relative;transition:.35s">` +
        `${a.icon}<div class="c-react" style="position:absolute;top:-7px;right:14px;width:20px;height:20px;border-radius:50%;` +
        `display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;background:rgba(6,12,22,.9)"></div></div>` +
        `<div style="font-size:11.5px;font-weight:600;margin-top:8px;color:#dbe7f6">${a.name}</div>` +
        `<div style="font-size:9.5px;color:#6f88a6;margin-top:1px">${a.role}</div>`;
      hud.appendChild(n); nodeEls[a.id] = n;
    }
    // kicker (top-left)
    const kick = el('div');
    kick.style.cssText = 'position:absolute;top:22px;left:28px;font-size:10px;letter-spacing:5px;color:#5b7290;text-transform:uppercase';
    kick.innerHTML = 'BRANCHSCAPE · ACT 2 — <b style="color:#9fc4ff;font-weight:600">THE COUNCIL</b>';
    hud.appendChild(kick);
    // phase label (top-right)
    const phase = el('div'); phase.id = 'c-phase';
    phase.style.cssText = 'position:absolute;top:20px;right:28px;font-size:13px;color:#ffd86b;font-weight:600;letter-spacing:1px';
    hud.appendChild(phase);
    // confidence meter
    const meter = el('div');
    meter.style.cssText = 'position:absolute;top:48px;right:28px;width:212px';
    meter.innerHTML =
      `<div style="font-size:10.5px;color:#8aa0bb;display:flex;justify-content:space-between"><span>TEAM CONFIDENCE</span><span id="c-front" style="color:#cfe0f5"></span></div>` +
      `<div style="height:7px;border-radius:4px;background:#10223a;margin-top:6px;overflow:hidden;border:1px solid #16304c"><div id="c-fill" style="height:100%;width:0;border-radius:4px;background:linear-gradient(90deg,#ff7e7e,#ffb86b,#6ad6b0);transition:width .9s ease"></div></div>` +
      `<div id="c-delta" style="font-size:10.5px;color:#8aa0bb;text-align:right;margin-top:5px;min-height:13px"></div>`;
    hud.appendChild(meter);
    // caption (lower third)
    const cap = el('div');
    cap.style.cssText = 'position:absolute;left:50%;bottom:118px;transform:translateX(-50%);width:680px;max-width:80vw;text-align:center';
    cap.innerHTML = `<div id="c-who" style="font-size:11px;letter-spacing:2px;text-transform:uppercase;font-weight:700;min-height:14px"></div><div id="c-line" style="font-size:18px;line-height:1.5;margin-top:9px;color:#f1f6ff;min-height:54px"></div>`;
    hud.appendChild(cap);
    // redirect bar
    const bar = el('div');
    bar.style.cssText = 'position:absolute;bottom:24px;left:34px;right:34px;height:54px;background:linear-gradient(90deg,rgba(16,28,46,.93),rgba(20,34,56,.93));border:1px solid #234266;border-radius:28px;display:flex;align-items:center;padding:0 22px;gap:14px;pointer-events:auto;box-shadow:0 0 30px rgba(10,30,60,.4)';
    bar.innerHTML = `<div style="font-size:10.5px;letter-spacing:2px;color:#5b7290;text-transform:uppercase;white-space:nowrap">YOU / THE ROOM ▸</div><input id="c-input" placeholder="Pose the question, or steer the council…  (e.g. weight community access higher)" style="flex:1;background:transparent;border:none;outline:none;color:#cfe0f5;font-size:14px;font-style:italic"><div id="c-send" style="background:#1c66ff;color:#fff;font-size:12px;font-weight:600;padding:9px 18px;border-radius:18px;cursor:pointer;white-space:nowrap">Redirect →</div>`;
    hud.appendChild(bar);
  }

  function setPhase(label) { const e = document.getElementById('c-phase'); if (e) e.textContent = label; }

  function setActiveSpeaker(agentId, line) {
    for (const id in nodeEls) {
      const orb = nodeEls[id].querySelector('.c-orb');
      const c = orb.style.getPropertyValue('--c');
      const active = id === agentId;
      orb.style.opacity = active ? '1' : '.55';
      orb.style.transform = active ? 'scale(1.22)' : 'scale(1)';
      orb.style.boxShadow = active ? `0 0 40px 9px ${c}` : `0 0 16px ${c}44`;
    }
    const a = window.COUNCIL_AGENTS.find(x => x.id === agentId);
    const who = document.getElementById('c-who'), ln = document.getElementById('c-line');
    if (who) { who.textContent = a ? a.name : ''; who.style.color = a ? a.color : '#fff'; }
    if (ln) ln.textContent = line || '';
  }

  function setReactions(map) { // {agentId:'agree'|'object'|'think'|'conditional'}
    const glyph = { agree: '✓', object: '✕', think: '…', conditional: '~' };
    const col = { agree: '#7dffb0', object: '#ff9b9b', think: '#9fc4ff', conditional: '#ffd86b' };
    for (const id in nodeEls) {
      const r = nodeEls[id].querySelector('.c-react');
      const v = map && map[id];
      r.textContent = v ? (glyph[v] || '') : '';
      r.style.color = v ? (col[v] || '#fff') : 'transparent';
      r.style.border = v ? `1px solid ${col[v] || '#fff'}66` : '1px solid transparent';
    }
  }

  function setConfidence(pct, frontLabel, deltaText) {
    const fill = document.getElementById('c-fill');
    if (fill) fill.style.width = Math.max(0, Math.min(100, pct)) + '%';
    const f = document.getElementById('c-front'); if (f) f.textContent = frontLabel || '';
    const d = document.getElementById('c-delta'); if (d) d.textContent = deltaText || '';
  }

  function showChips(chips) { // [{lon,lat,text,danger}]
    document.querySelectorAll('.c-chip').forEach(e => e.remove());
    for (const c of chips) {
      const [x, y] = CouncilMap.projectToScreen(c.lon, c.lat);
      const chip = el('div', 'c-chip', c.text);
      chip.style.cssText = `position:absolute;left:${x}px;top:${y}px;transform:translate(-50%,-150%);font-size:10px;padding:4px 9px;border-radius:12px;white-space:nowrap;background:rgba(14,28,48,.92);border:1px solid ${c.danger ? '#6e2c2c' : '#1e3a5c'};color:${c.danger ? '#ffb3b3' : '#bcd4f0'};box-shadow:0 0 14px rgba(10,30,60,.5)`;
      hud.appendChild(chip);
    }
  }

  function attackBeam(fromAgentId, lon, lat) {
    document.querySelectorAll('.c-beam').forEach(e => e.remove());
    const node = nodeEls[fromAgentId]; if (!node) return;
    const nr = node.getBoundingClientRect();
    const [tx, ty] = CouncilMap.projectToScreen(lon, lat);
    const x1 = nr.left + nr.width / 2, y1 = nr.top + 32;
    const len = Math.hypot(tx - x1, ty - y1), ang = Math.atan2(ty - y1, tx - x1) * 180 / Math.PI;
    const beam = el('div', 'c-beam');
    beam.style.cssText = `position:absolute;left:${x1}px;top:${y1}px;height:3px;width:${len}px;transform-origin:left center;transform:rotate(${ang}deg);background:linear-gradient(90deg,#ff5a5a,rgba(255,120,120,.12));box-shadow:0 0 14px 2px rgba(255,80,80,.55);border-radius:2px`;
    hud.appendChild(beam);
    setTimeout(() => beam.remove(), 2600);
  }

  function clearTransient() { document.querySelectorAll('.c-chip,.c-beam').forEach(e => e.remove()); }

  return { mount, setPhase, setActiveSpeaker, setReactions, setConfidence, showChips, attackBeam, clearTransient };
})();
