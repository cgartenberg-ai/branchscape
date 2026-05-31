// branchscape/council/live.js
(function (global) {
  function initialState() {
    return { beat: null, activeAgent: null, caption: '', lastMessage: null, votes: [], verdict: null };
  }
  // Pure: (state, event) -> state. No DOM. This is the single source of truth.
  function applyEvent(state, evt) {
    const s = Object.assign({}, state);
    switch (evt.type) {
      case 'phase_change': s.beat = evt.data.beat; break;
      case 'agent_thinking':
        if (evt.agent !== s.activeAgent) { s.activeAgent = evt.agent; s.caption = ''; }
        s.caption = (s.caption || '') + (evt.data.text || '');
        break;
      case 'agent_message':
        s.activeAgent = evt.agent;
        s.lastMessage = { agent: evt.agent, text: evt.data.text };
        s.caption = evt.data.text;
        break;
      case 'tool_call': s.lastTool = { agent: evt.agent, name: evt.data.name, input: evt.data.input }; break;
      case 'tool_result': s.lastToolResult = { agent: evt.agent, name: evt.data.name, result: evt.data.result }; break;
      case 'vote_cast': s.votes = s.votes.concat([Object.assign({ agent: evt.agent }, evt.data)]); break;
      case 'verdict': s.verdict = evt.data; break;
      default: break;
    }
    return s;
  }

  // Browser-only: connect SSE and render each event into the existing HUD.
  function connect(opts) {
    let state = initialState();
    const es = new EventSource('/events');
    es.onmessage = (m) => {
      const evt = JSON.parse(m.data);
      state = applyEvent(state, evt);
      render(evt, state);
    };
    es.onerror = () => { if (opts && opts.onError) opts.onError(); };
    return {
      start: (mandate) => fetch('/control', { method: 'POST', body: JSON.stringify({ action: 'start', mandate }) }),
      callQuestion: () => fetch('/control', { method: 'POST', body: JSON.stringify({ action: 'call_question' }) }),
      state: () => state,
    };
  }
  const STANCE_REACTION = { support: 'agree', oppose: 'object', conditional: 'conditional' };
  function render(evt, state) {
    if (typeof CouncilUI === 'undefined') return;
    if (evt.type === 'phase_change') CouncilUI.setPhase('LIVE · ' + state.beat.toUpperCase());
    if (evt.type === 'agent_thinking') CouncilUI.setActiveSpeaker(state.activeAgent, state.caption);
    if (evt.type === 'agent_message') CouncilUI.setActiveSpeaker(evt.agent, evt.data.text);
    if (evt.type === 'tool_call' && typeof CouncilUI.showToolChip === 'function') {
      const label = evt.data.name + (evt.data.input && evt.data.input.metric ? '(' + evt.data.input.metric + ')' : '');
      CouncilUI.showToolChip(evt.agent, label);
    }
    if (evt.type === 'vote_cast') {
      const react = {};
      for (const v of state.votes) react[v.agent] = STANCE_REACTION[v.stance] || 'think';
      CouncilUI.setReactions(react);
    }
    if (evt.type === 'verdict') { CouncilUI.setActiveSpeaker('chair', evt.data.text); CouncilUI.setPhase('VERDICT'); }
  }

  const api = { initialState, applyEvent, connect };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else global.CouncilLive = api;
})(typeof window !== 'undefined' ? window : globalThis);
