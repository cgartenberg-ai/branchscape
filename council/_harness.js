// council/_harness.js — minimal zero-dependency test harness.
// Why not node:test? On this machine (macOS 26 beta + Node 22) the built-in
// `node --test` runner reports spurious failures and segfaults on teardown,
// even when assertions pass. Plain node:assert runs reliably, so we run tests
// synchronously in-process and exit explicitly.
//
// Usage in a *.test.js file:
//   const assert = require('node:assert');
//   const { test, report } = require('./_harness.js');
//   test('does the thing', () => { assert.strictEqual(f(), 1); });
//   report();   // <-- prints summary and sets exit code; call once at the end
//
// Run:  node council/<name>.test.js     (exit 0 = pass, 1 = fail)

let passed = 0, failed = 0;
const failures = [];

function test(name, fn) {
  try {
    const r = fn();
    if (r && typeof r.then === 'function') {
      throw new Error('async tests are not supported by this harness');
    }
    passed++;
    console.log('  ✓ ' + name);
  } catch (e) {
    failed++;
    const msg = (e && e.message) ? e.message : String(e);
    failures.push(name + ': ' + msg);
    console.log('  ✖ ' + name);
  }
}

function report() {
  console.log(`\ntests ${passed + failed} / pass ${passed} / fail ${failed}`);
  for (const f of failures) console.log('  ✖ ' + f);
  process.exit(failed ? 1 : 0);
}

module.exports = { test, report };
