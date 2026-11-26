# Preserve Eval

We give a candidate a base mesh and one narrowly defined job: mark the
seam edges, and change **nothing else**. We grade the result against the
base mesh itself — vertex by vertex, face by face, UV by UV — plus a
fuzzy shape comparison and a standalone sanity pass.

Preserve Eval is a long-horizon discipline test disguised as a small
task. Most mesh tooling fails it quietly: a re-export reorders vertices,
a cleanup pass moves coordinates, an "identical" output drifts. This
benchmark makes preservation the headline score, names the exact channel
that changed when it fails, and scores seam marking on hidden held-out
meshes that are never published.

The full task contract is in [`spec/TASK.md`](spec/TASK.md).

## Layout

The repository follows a seven-part layout:

| Part | Contents |
|---|---|
| `spec/` | The task contract (`TASK.md`): inputs, outputs, edge indexing, permitted changes, scoring, failure conditions. |
| `corpus/` | The grading cases: each case is a base mesh, case metadata, and section weights in a single configuration file. Published cases are examples; real scoring uses held-out cases. |
| `reference/` | The reference for every case is its own base mesh, plus reference seam sets for held-out cases. Grading is a diff against the base, not a set of hand-written assertions. |
| `harness/` | The grader: parses base and candidate OBJ files, assigns edge indices, diffs every channel, computes the section scores, and writes per-case JSON plus a summary. |
| `candidates/` | Candidate implementations. A deliberately partial baseline is included so a fresh clone can grade something out of the box. |
| `quickstart/` | One-command grading and a short smoke test. No build step beyond the harness's own dependencies. |
| `results/` | Grading output: one directory per run, with per-case JSON results and a `summary.json` leaderboard-style record. |

## How grading works

```bash
# Per candidate: grade the output directory against the corpus.
# Writes results/<candidate>/<case>.json per case, plus summary.json.
./quickstart/grade.sh candidates/baseline
```

For each case the grader:

1. Parses `base.obj` and the candidate's `after.obj`, and builds the
   edge index from the base faces (sorted vertex-index pairs, in order
   of first appearance).
2. Diffs the candidate against the base channel by channel — vertex
   coordinates, vertex order, face structure, UVs — and reads the
   candidate's seam set from `after.seams`.
3. Runs a fuzzy shape comparison (candidate shape vs. base shape) and
   an intrinsic sanity pass over the output.
4. Emits a per-case JSON result naming every differing channel, and a
   summary with the weighted overall score.

## Scoring: three sections

The overall score is the weighted sum of three independent sections.
Weights are configurable in the corpus configuration; the defaults are:

| Section | Weight | What it measures |
|---|---|---|
| **Preservation** | 60% | Exact channel-by-channel match of `after.obj` against `base.obj`: coordinates, order, faces, UVs. |
| **Shape** | 25% | Fuzzy geometric agreement between the candidate mesh and the base shape, within a fixed tolerance. |
| **Intrinsic** | 15% | Standalone mesh sanity: parseable, self-consistent, no degenerate geometry introduced. |

```
overall = 0.60 × preservation + 0.25 × shape + 0.15 × intrinsic
```

Cases can fail outright — missing or unparseable outputs, duplicate or
out-of-range seam indices, added/removed/reordered elements — as
specified in the task contract.

## Quickstart

```bash
./quickstart/smoke-test.sh     # preflight: layout, corpus, baseline present
./quickstart/grade.sh candidates/baseline
```

The smoke test verifies the repository layout and that the baseline
candidate can be graded end to end. Grading output lands in
`results/baseline/` — per-case JSON and `summary.json` with the overall
score.

## What is not included

- **No `.blend` / Blender stage yet.** Grading operates on OBJ files.
  Where Blender 4.2 is available, roundtrip-doctor plugs in as an
  additional preservation stage for native `.blend` round trips; it is
  an optional stage, not a requirement of this repository.
- **No supervisor or checkpointing layer.** Long-run supervision,
  auto-checkpointing of candidate work, per-run hosting, and access
  control for held-out cases live outside this repository. The
  quickstart grades a finished candidate output; it does not run or
  babysit the candidate.
- **No held-out cases.** The published corpus is example material.
  The cases used for real scoring are not in this repository.

## License

Original work in this repository is MIT licensed. Third-party meshes or
tools included in the corpus or harness retain their own licenses,
noted where they appear.
