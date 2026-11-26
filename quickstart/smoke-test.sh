#!/bin/bash
# 30-second preflight: fixtures present + hash-pinned, grader imports,
# baseline candidate grades as PASS and sloppy candidate grades as FAIL.
set -e
cd "$(dirname "$0")/.."
python3 - <<'EOF'
import hashlib, json
corpus = json.load(open("corpus/testcases.json"))
for tc in corpus["testcases"]:
    data = open("corpus/" + tc["base"], "rb").read()
    assert hashlib.sha256(data).hexdigest() == tc["base_sha256"], tc["id"]
    print("fixture ok:", tc["id"])
EOF
python3 harness/grader.py candidates/baseline/solve.py corpus results
if python3 harness/grader.py candidates/sloppy/solve.py corpus results; then
  echo "SMOKE FAIL: sloppy candidate unexpectedly passed"
  exit 1
fi
echo "SMOKE OK: baseline passes, sloppy fails, fixtures verified"
