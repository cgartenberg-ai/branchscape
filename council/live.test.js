// branchscape/council/live.test.js
const assert = require('node:assert');
const { test, report } = require('./_harness.js');
const { applyEvent, initialState } = require('./live.js');

test('agent_thinking appends streamed text for the active agent', () => {
  let s = initialState();
  s = applyEvent(s, { type: 'phase_change', data: { beat: 'positions' } });
  s = applyEvent(s, { type: 'agent_thinking', agent: 'market', data: { text: 'Buck' } });
  s = applyEvent(s, { type: 'agent_thinking', agent: 'market', data: { text: 'eye' } });
  assert.strictEqual(s.activeAgent, 'market');
  assert.strictEqual(s.caption, 'Buckeye');
  assert.strictEqual(s.beat, 'positions');
});

test('agent_message finalizes the line and a new agent_thinking resets caption', () => {
  let s = initialState();
  s = applyEvent(s, { type: 'agent_thinking', agent: 'market', data: { text: 'hi' } });
  s = applyEvent(s, { type: 'agent_message', agent: 'market', data: { text: 'hi there' } });
  assert.strictEqual(s.lastMessage.text, 'hi there');
  s = applyEvent(s, { type: 'agent_thinking', agent: 'risk', data: { text: 'X' } });
  assert.strictEqual(s.activeAgent, 'risk');
  assert.strictEqual(s.caption, 'X');
});

report();
