#!/bin/bash
# Phase 2: baseline passes, every seeded failure case is caught by its named section — on the public corpus and on hidden variants.
set -e
cd "$(dirname "$0")/.."
python3 corpus/gen_hidden.py
python3 harness/phase2_check.py
python3 harness/phase2_check.py corpus-hidden
