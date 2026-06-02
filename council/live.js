// branchscape/council/live.js
(function (global) {
  function initialState() {
    return { beat: null, activeAgent: null, caption: '', lastMessage: null,
             votes: [], verdict: null, lastError: null, done: false,
             reportPending: false, artifacts: null };
  }

  // Pure: build a non-empty conclusion string from a verdict payload. Uses the
  // chair's prose when present; otherwise derives a summary from the tally + the
  // most-voted zone — so the ending is NEVER blank (the live-run stall was an
  // empty chair synthesis rendering as a blank caption).
  function verdictText(d) {
    d = d || {};
    const t = (d.text || '').trim();
    if (t) return t;
    const tally = d.tally || {};
    const parts = Object.keys(tally).map(k => tally[k] + ' ' + k).join(', ');
    let zone = null, best = -1;
    const counts = {};
    for (const v of (d.votes || [])) {
      if (!v.zone) continue;
      counts[v.zone] = (counts[v.zone] || 0) + 1;
      if (counts[v.zone] > best) { best = counts[v.zone]; zone = v.zone; }
    }
    const where = zone ? ('tract ' + String(zone).slice(-4)) : 'no clear front-runner';
    return 'The council has voted' + (parts ? ' (' + parts + ')' : '') + '. Recommendation: ' + where + '.';
  }

  // Pure: (state, event) -> state. No DOM. The single source of truth.
  function applyEvent(state, evt) {
    const s = Object.assign({}, state);
    switch (evt.type) {
      case 'phase_change': s.beat = evt.data.beat; break;
      case 'agent_thinking':
        if (evt.agent !== s.activeAgent) { s.activeAgent = evt.agent; s.caption = ''; }
        s.caption = (s.caption || '') + (evt.data.text || '');
        break;
      case 'agent_message': {
        const txt = (evt.data && evt.data.text) || '';
        if (txt) {  // ignore empty messages so they can't blank the caption
          s.activeAgent = evt.agent;
          s.lastMessage = { agent: evt.agent, text: txt };
          s.caption = txt;
        }
        break;
      }
      case 'tool_call': s.lastTool = { agent: evt.agent, name: evt.data.name, input: evt.data.input }; break;
      case 'tool_result': s.lastToolResult = { agent: evt.agent, name: evt.data.name, result: evt.data.result }; break;
      case 'vote_cast': s.votes = s.votes.concat([Object.assign({ agent: evt.agent }, evt.data)]); break;
      // The decision memo is generated AFTER the verdict (a second model call), so mark it
      // pending here; the artifacts event clears it once the memo + transcript are written.
      case 'verdict': s.verdict = evt.data; s.reportPending = true; break;
      case 'error': s.lastError = { agent: evt.agent, message: (evt.data && evt.data.message) || 'error' }; break;
      case 'artifacts': s.artifacts = evt.data; s.reportPending = false; break;
      case 'run_end': s.done = true; break;
      default: break;
    }
    return s;
  }

  // Browser-only: connect SSE and render each event into the existing HUD.
  function connect(opts) {
    let state = initialState();
    const es = new EventSource('/events');
    es.onmessage = (m) => {
      let evt; try { evt = JSON.parse(m.data); } catch (e) { return; }
      state = applyEvent(state, evt);
      // a render slip must never stop the stream — but surface it so it isn't silent
      try { render(evt, state); } catch (e) { try { console.warn('[council] render error', evt && evt.type, e); } catch (_) {} }
    };
    es.onerror = () => { if (opts && opts.onError) opts.onError(); };
    return {
      start: (mandate, profile) => fetch('/control', { method: 'POST', body: JSON.stringify({ action: 'start', mandate, profile }) }),
      callQuestion: () => fetch('/control', { method: 'POST', body: JSON.stringify({ action: 'call_question' }) }),
      replay: () => fetch('/control', { method: 'POST', body: JSON.stringify({ action: 'replay' }) }),
      state: () => state,
    };
  }

  const STANCE_REACTION = { support: 'agree', oppose: 'object', conditional: 'conditional' };
  function render(evt, state) {
    if (typeof CouncilUI === 'undefined') return;
    if (evt.type === 'phase_change') CouncilUI.setPhase('LIVE · ' + state.beat.toUpperCase());
    if (evt.type === 'agent_thinking') CouncilUI.setActiveSpeaker(state.activeAgent, state.caption);
    if (evt.type === 'agent_message' && evt.data && (evt.data.text || '').trim())
      CouncilUI.setActiveSpeaker(evt.agent, evt.data.text);
    if (evt.type === 'tool_call' && typeof CouncilUI.showToolChip === 'function') {
      const label = evt.data.name + (evt.data.input && evt.data.input.metric ? '(' + evt.data.input.metric + ')' : '');
      CouncilUI.showToolChip(evt.agent, label);
    }
    if (evt.type === 'vote_cast') {
      const react = {};
      for (const v of state.votes) react[v.agent] = STANCE_REACTION[v.stance] || 'think';
      CouncilUI.setReactions(react);
    }
    if (evt.type === 'verdict') {
      CouncilUI.setActiveSpeaker('chair', verdictText(evt.data));  // never blank
      CouncilUI.setPhase('VERDICT');
      // the memo is still being written server-side — show a pending cue so the
      // report doesn't look like it never arrived during that ~30-40s gap.
      if (typeof CouncilUI.showArtifacts === 'function') CouncilUI.showArtifacts(null, true);
    }
    if (evt.type === 'error') {
      CouncilUI.setPhase('⚠ ERROR');
      CouncilUI.setActiveSpeaker(evt.agent || 'chair', '⚠ ' + ((evt.data && evt.data.message) || 'error'));
    }
    if (evt.type === 'run_end' && !state.verdict) CouncilUI.setPhase('DONE');
    if (evt.type === 'artifacts' && typeof CouncilUI.showArtifacts === 'function')
      CouncilUI.showArtifacts(evt.data);
  }

  const api = { initialState, applyEvent, verdictText, connect };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else global.CouncilLive = api;
})(typeof window !== 'undefined' ? window : globalThis);
