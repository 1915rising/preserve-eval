#!/bin/bash
# Grade a candidate solver: grade.sh <path-to-solve.py> [candidate-name]
set -e
cd "$(dirname "$0")/.."
SOLVER="${1:?usage: grade.sh <path-to-solve.py>}"
python3 harness/grader.py "$SOLVER" corpus results
