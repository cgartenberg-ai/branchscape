// council/_harness.js — zero-dependency test harness, hardened for this machine.
//
// WHY THIS EXISTS (read before "simplifying" back to node --test):
// On this box (macOS 26 beta / Darwin 25 + Node 22) EVERY node process
// segfaults on teardown — `node -e "console.log('hi')"` prints "hi" then exits
// 139. That makes the process EXIT CODE useless as a pass/fail signal, and a
// teardown segfault can also corrupt piped STDOUT. So we do not trust either.
//
// Ground truth = a result file written SYNCHRONOUSLY with fs.writeFileSync
// (completes and flushes to disk before the JS finishes and the crash happens).
// `--jitless` usually avoids the segfault too, so run tests with it for clean
// console output, but the file is the authoritative gate.
//
// Test-file convention:
//   const assert = require('node:assert');
//   const { test, report } = require('./_harness.js');
//   test('does the thing', () => { assert.strictEqual(f(), 1); });
//   report();   // <-- MUST be the last line; writes the result file + summary
//
// Run one file:   node --jitless council/<name>.test.js
// Run all:        ./run-tests.sh           (from the branchscape folder)
// Gate (per file): council/.last-test-result contains "fail=0".

const fs = require('node:fs');
const path = require('node:path');

let passed = 0, failed = 0;
const failures = [];

function test(name, fn) {
  try {
    const r = fn();
    if (r && typeof r.then === 'function') {
      throw new Error('async tests are not supported by this harness');
    }
    passed++;
    console.log('  PASS  ' + name);
  } catch (e) {
    failed++;
    const msg = (e && e.message) ? e.message : String(e);
    failures.push(name + ': ' + msg);
    console.log('  FAIL  ' + name + '  -- ' + msg);
  }
}

function report() {
  const summary = `RESULT tests=${passed + failed} pass=${passed} fail=${failed}`;
  console.log('\n' + summary);
  for (const f of failures) console.log('  FAIL  ' + f);
  // Durable, corruption-proof signal (survives a teardown segfault):
  try {
    fs.writeFileSync(path.join(__dirname, '.last-test-result'), summary + '\n');
  } catch (_) { /* ignore */ }
  process.exit(failed ? 1 : 0);
}

module.exports = { test, report };
