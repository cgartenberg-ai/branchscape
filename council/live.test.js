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

test('tool_call/tool_result tracked; vote carries agent; verdict captured', () => {
  let s = initialState();
  s = applyEvent(s, { type: 'tool_call', agent: 'market', data: { name: 'query_data', input: { metric: 'branch_count' } } });
  assert.strictEqual(s.lastTool.name, 'query_data');
  s = applyEvent(s, { type: 'vote_cast', agent: 'risk', data: { zone: '0401301', stance: 'oppose', rationale: 'saturated' } });
  assert.strictEqual(s.votes[0].agent, 'risk');
  assert.strictEqual(s.votes[0].stance, 'oppose');
  s = applyEvent(s, { type: 'verdict', agent: 'chair', data: { text: 'We recommend X', votes: [] } });
  assert.strictEqual(s.verdict.text, 'We recommend X');
});

report();
