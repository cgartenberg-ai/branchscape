// branchscape/council/director.js  (browser-only)
// The 5-beat choreographer. Orchestrates engine + map + ui + script:
// recomputes the decision from a mandate, then walks mandate → gather →
// positions → crossExam → verdict, driving the HUD each beat. Presenter
// controls (Space/→/R) and an anytime audience redirect re-deliberate live.
const Director = (function () {
  const BEATS = ['mandate', 'gather', 'positions', 'crossExam', 'verdict'];
  const PHASE_LABEL = {
    mandate: 'BEAT 1 · THE MANDATE', gather: 'BEAT 2 · GATHERING DATA',
    positions: 'BEAT 3 · OPENING POSITIONS', crossExam: 'BEAT 4 · CROSS-EXAMINATION',
    verdict: 'BEAT 5 · THE VOTE',
  };
  const SPEAK_MS = 3400;
  let mandate, ranked, challenge, confBefore, confAfter,
      beatIdx = 0, lineIdx = 0, playing = false, timer = null;

  const data = () => ({ tracts: window.TRACTS, branches: window.BRANCH_DATA.branches,
    craTract: window.CRA_TRACT, income: window.INCOME_DATA });
  const labelFor = z => z ? ('tract ' + z.geoid.slice(-4)) : '—'; // Phase 3 maps to place names

  function recompute(text) {
    const E = window.CouncilEngine;
    mandate = window.CouncilMandate.parseMandate(text);
    const zones = E.normalizeZones(E.deriveSignals(E.buildZones(data())));
    ranked = E.rankZones(zones, mandate.weights);
    challenge = E.devilsChallenge(ranked, mandate.weights);
    confBefore = E.computeConfidence(ranked, window.COUNCIL_AGENTS);
    confAfter = E.computeConfidence(E.applyChallenge(ranked, challenge), window.COUNCIL_AGENTS);
    CouncilMap.setZones(ranked);
    CouncilMap.dropPins(ranked.slice(0, 3));
  }
  function fill(text) {
    const front = labelFor(ranked[0]), runner = labelFor(ranked[1] || ranked[0]);
    return text.replace(/{front}/g, front).replace(/{runner}/g, runner)
      .replace(/{confFinal}/g, confAfter).replace(/{conf}/g, confBefore)
      .replace(/{dim}/g, challenge.dimension);
  }

  function applyBeatVisuals(beat) {
    CouncilUI.setPhase(PHASE_LABEL[beat]);
    if (beat === 'mandate') {
      CouncilMap.setOverlay('gap', false); CouncilMap.setOverlay('saturation', false); CouncilMap.setOverlay('community', false);
      CouncilUI.clearTransient(); CouncilUI.setReactions({});
      CouncilUI.setConfidence(0, '', '');
    }
    if (beat === 'gather') {
      CouncilMap.setOverlay('gap', true); CouncilMap.setOverlay('saturation', true); CouncilMap.setOverlay('community', true);
      const top = ranked[0];
      CouncilUI.showChips([
        { lon: top.lon, lat: top.lat, text: 'widest deposit gap' },
        { lon: top.lon, lat: top.lat, text: 'CRA-eligible' },
      ]);
      CouncilUI.setReactions({ market: 'think', risk: 'think', community: 'think', realestate: 'think' });
    }
    if (beat === 'positions') {
      CouncilUI.setConfidence(confBefore, labelFor(ranked[0]), '');
      CouncilUI.setReactions({ market: 'agree', community: 'agree', realestate: 'agree', risk: 'think' });
    }
    if (beat === 'crossExam') {
      CouncilUI.attackBeam('devil', ranked[0].lon, ranked[0].lat);
      CouncilUI.setConfidence(confAfter, labelFor(ranked[0]), `▼ ${confBefore}% → ${confAfter}%  (challenged)`);
      CouncilUI.setReactions({ risk: 'agree', market: 'think', community: 'object', realestate: 'think' });
    }
    if (beat === 'verdict') {
      const votes = window.CouncilEngine.computeVotes(ranked[0], window.COUNCIL_AGENTS);
      const react = {};
      for (const v of votes) react[v.id] = v.vote === 'no' ? 'object' : (v.vote === 'conditional' ? 'conditional' : 'agree');
      react.chair = 'agree';
      CouncilUI.setReactions(react);
      CouncilUI.setConfidence(confAfter, labelFor(ranked[0]), 'RECOMMENDATION');
    }
  }

  function playLine() {
    const beat = BEATS[beatIdx];
    const lines = window.COUNCIL_SCRIPT.beats[beat];
    if (lineIdx === 0) applyBeatVisuals(beat);
    if (lineIdx >= lines.length) { return nextBeat(); }
    const ln = lines[lineIdx++];
    CouncilUI.setActiveSpeaker(ln.agent, fill(ln.text));
    if (playing) timer = setTimeout(playLine, SPEAK_MS);
  }
  function nextBeat() {
    if (beatIdx < BEATS.length - 1) { beatIdx++; lineIdx = 0; playLine(); }
    else { playing = false; }
  }

  function start(text) {
    recompute(text || '');
    beatIdx = 0; lineIdx = 0; playing = true;
    CouncilUI.mount();
    playLine();
  }
  function play() { if (!playing) { playing = true; playLine(); } }
  function pause() { playing = false; clearTimeout(timer); }
  function step() { pause(); playLine(); }

  // Interrupt: re-pose / steer, then re-deliberate from the cross-examination.
  function redirect(text) {
    pause();
    recompute(text);
    beatIdx = BEATS.indexOf('crossExam'); lineIdx = 0;
    CouncilUI.clearTransient();
    CouncilUI.setPhase('RE-DELIBERATING…');
    CouncilUI.setActiveSpeaker('chair', 'New direction from the room — re-running the numbers on ' + labelFor(ranked[0]) + '…');
    playing = true;
    timer = setTimeout(playLine, 1600);
  }

  function wireControls() {
    document.addEventListener('keydown', e => {
      if (e.target && e.target.id === 'c-input') return;
      if (e.code === 'Space') { e.preventDefault(); playing ? pause() : play(); }
      if (e.code === 'ArrowRight') { e.preventDefault(); step(); }
      if (e.key === 'r' || e.key === 'R') { start(mandate ? mandate.label : ''); }
    });
    const send = () => {
      const inp = document.getElementById('c-input');
      const v = inp.value.trim();
      if (v) { redirect(v); inp.value = ''; inp.blur(); }
    };
    document.getElementById('c-send').addEventListener('click', send);
    document.getElementById('c-input').addEventListener('keydown', e => {
      if (e.code === 'Enter') { e.preventDefault(); send(); }
    });
  }

  return { start, play, pause, step, redirect, wireControls };
})();
