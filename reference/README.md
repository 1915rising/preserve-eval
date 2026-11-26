# Reference

The known-good bases. Every corpus testcase pins its base by SHA-256 in
`corpus/testcases.json`; the grader refuses to grade against a base whose
hash does not match (filenames do not matter, contents do).

- `cube.obj` — UV-mapped cube, watertight, quad faces.
- `icosphere.obj` — subdivided icosphere, watertight, no UVs.
- `open-box.obj` — cube missing its top face; not watertight by design, so
  the intrinsic section has a real defect to report.

Regenerate with `python3 corpus/gen_fixtures.py` (deterministic; hashes in
testcases.json are rewritten to match). Hidden held-out bases for real
scoring are NOT kept in this repo.
