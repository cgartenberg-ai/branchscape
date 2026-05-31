#!/bin/zsh
# Run all council/*.test.js and gate on the durable result file each writes,
# NOT on exit code or stdout (both are unreliable here — see council/_harness.js).
cd "${0:A:h}"   # branchscape folder
overall=0
for f in council/*.test.js; do
  rm -f council/.last-test-result
  node --jitless "$f" 2>/dev/null
  res=$(cat council/.last-test-result 2>/dev/null)
  if [[ "$res" == *"fail=0"* && "$res" == *"pass="* ]]; then
    echo "PASS  $f   ($res)"
  else
    echo "FAIL  $f   (${res:-no result file written})"
    overall=1
  fi
done
echo "----"
if [[ $overall -eq 0 ]]; then echo "ALL TESTS PASS"; else echo "SOME TESTS FAILED"; fi
exit $overall
