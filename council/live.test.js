// branchscape/council/live.test.js
const assert = require('node:assert');
const { test, report } = require('./_harness.js');
const { applyEvent, initialState, verdictText } = require('./live.js');

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

test('empty agent_message does NOT blank the caption (keeps the last real line)', () => {
  let s = initialState();
  s = applyEvent(s, { type: 'agent_message', agent: 'chair', data: { text: "I'll synthesize and call the vote." } });
  assert.strictEqual(s.caption, "I'll synthesize and call the vote.");
  s = applyEvent(s, { type: 'agent_message', agent: 'chair', data: { text: '' } }); // the bug: empty msg
  assert.strictEqual(s.caption, "I'll synthesize and call the vote.", 'empty message must not blank caption');
});

test('error captured (never silent); run_end marks done', () => {
  let s = initialState();
  s = applyEvent(s, { type: 'error', agent: 'chair', data: { message: 'chair turn failed: boom' } });
  assert.ok(s.lastError && /boom/.test(s.lastError.message));
  s = applyEvent(s, { type: 'run_end', data: {} });
  assert.strictEqual(s.done, true);
});

test('verdictText falls back to a tally summary when chair text is empty', () => {
  // the live-run stall: empty verdict text must still produce a VISIBLE conclusion
  const empty = verdictText({ text: '', tally: { support: 4, oppose: 1 },
                              votes: [{ zone: '04013004705', stance: 'support' }] });
  assert.ok(empty && empty.length > 0, 'must derive non-empty text');
  assert.ok(/4 support/.test(empty));
  // and uses the chair's real text when present
  assert.strictEqual(verdictText({ text: 'Recommend tract 4705.', tally: {} }), 'Recommend tract 4705.');
});

test('verdict marks the decision memo as pending; artifacts clears it and stores urls', () => {
  // The server generates the memo AFTER the verdict (a second model call), so the UI
  // must show a "generating…" state in between or the report looks like it never came.
  let s = initialState();
  assert.strictEqual(s.reportPending, false);
  s = applyEvent(s, { type: 'verdict', agent: 'chair', data: { text: 'Recommend X', votes: [] } });
  assert.strictEqual(s.reportPending, true, 'memo is generating right after the verdict');
  s = applyEvent(s, { type: 'artifacts', data: { report: '/runs/r-report.md', transcript: '/runs/r-transcript.md' } });
  assert.strictEqual(s.reportPending, false, 'memo arrived');
  assert.strictEqual(s.artifacts.report, '/runs/r-report.md');
});

test('room_inject records the presenter/room message so the HUD can show the redirect', () => {
  let s = initialState();
  s = applyEvent(s, { type: 'room_inject', data: { text: 'weight community access higher' } });
  assert.strictEqual(s.lastRoom, 'weight community access higher');
});

report();
