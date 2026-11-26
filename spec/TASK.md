# Preserve the Base — Task Contract

## Purpose

This task tests one ability: perform a single, narrowly defined operation
on a supplied mesh — marking seam edges — while preserving everything
else about that mesh exactly. A candidate that changes any vertex,
reorders any element, or alters any face or UV fails the preservation
requirement no matter how good its seam choices are.

The contract below is complete. Everything a candidate is scored on is
stated here; nothing is scored that is not stated here. A human expert
given the same inputs should be able to produce a perfect-scoring output
by following this document alone.

## Inputs

The candidate receives, per case:

| File | Description |
|---|---|
| `base.obj` | The base mesh in Wavefront OBJ format. This file is the reference for the case and is never modified. |
| `corpus/testcases.json` | Grader-side case manifest (id, base file, SHA-256 pin, description). Held by the grader, not supplied to the candidate. |

`base.obj` uses 1-based OBJ indices. Vertex lines (`v`), UV lines (`vt`),
and face lines (`f`) in `base.obj` define the canonical vertex order,
face structure, and UV layout for the case.

## Outputs

The candidate must produce exactly two files, in the case output
directory:

| File | Description |
|---|---|
| `after.obj` | The resulting mesh. Must be identical to `base.obj` in vertex coordinates, vertex order, face structure, and UVs (see Permitted Changes). |
| `after.seams` | The seam marking: a plain text file, one edge index per line, listing every edge the candidate marks as a seam. |

### Edge indexing

Edges are indexed deterministically from `base.obj`:

1. Read the faces of `base.obj` in file order.
2. For each face, walk its vertices in the order listed, forming an edge
   between each consecutive pair of vertices, and between the last
   vertex and the first.
3. An edge is an unordered pair of vertex indices; write it as the sorted
   pair `(min, max)` using the OBJ 1-based vertex indices.
4. The first time a given sorted pair appears, it is assigned the next
   edge index, starting at `0`. Later appearances of the same pair reuse
   that index.
5. Edge indices in `after.seams` refer to this indexing. Indices must be
   integers, one per line, with no duplicates. An empty `after.seams`
   (marking no seams) is a valid output and scores accordingly.

## Contract summary

1. Input is `base.obj` only; the base file is read-only.
2. Output is exactly `after.obj` and `after.seams`.
3. Seam marking is expressed **only** in `after.seams`.
4. `after.obj` must carry the same vertices, in the same order, with the
   same coordinates as `base.obj`.
5. `after.obj` must carry the same faces, in the same order, referencing
   the same vertices as `base.obj`.
6. `after.obj` must carry the same UVs, in the same order, with the same
   values as `base.obj`.
7. Edge indices are assigned by first appearance of the sorted
   vertex-index pair across `base.obj` faces, starting at `0`.
8. `after.seams` holds one integer edge index per line, no duplicates.
9. No other files, renames, or format changes are part of the output.
10. Any change outside the `.seams` sidecar is a preservation failure.

## Permitted changes

The **only** permitted change is the seam marking recorded in
`after.seams`. There are no permitted changes to `after.obj` itself:

- Vertex coordinates: identical.
- Vertex order and count: identical.
- Face structure (count, order, vertex references): identical.
- UV coordinates, order, and count: identical.

Reformatting that does not change any parsed value (for example,
whitespace or line-ending differences in `after.obj`) is not scored as a
change; grading compares parsed geometry, not raw bytes.

## Scoring

Each case is scored in three independent sections. Section scores are in
`[0, 1]` and combined as a weighted sum:

| Section | Weight | What it measures |
|---|---|---|
| Preservation | 0.60 | Whether `after.obj` matches `base.obj` exactly in vertex coordinates, vertex order, face structure, and UVs, channel by channel. Any non-permitted difference reduces this score; the grader names the failing channel. |
| Shape | 0.25 | Whether the candidate mesh, taken as a shape, still occupies the same geometry as the base — a fuzzy geometric comparison that tolerates no drift beyond a fixed tolerance, independent of file structure. |
| Intrinsic | 0.15 | Standalone mesh sanity of the output: well-formed faces, no degenerate geometry introduced, valid indices, and a parseable, self-consistent OBJ. |

```
overall = 0.60 × preservation + 0.25 × shape + 0.15 × intrinsic
```

The seam marking itself is evaluated as part of the case result: on
held-out cases, the candidate's seam set is compared against the
reference seam set for that mesh, and that comparison is reported
alongside the three sections above.

## What counts as failure

A case fails outright (overall score `0` for the case) if any of the
following holds:

- `after.obj` or `after.seams` is missing, empty where content is
  required, or cannot be parsed.
- `after.seams` contains a duplicate index, a non-integer line, or an
  edge index outside the range defined by `base.obj`.
- `after.obj` adds, removes, or reorders any vertex, face, or UV.

A case does **not** fail outright, but loses preservation credit
proportionally, if parsed values in `after.obj` differ from `base.obj`
in any channel (coordinates, face references, UV values). The grader
reports each differing channel separately so a partial result is always
explainable.

Producing extra files, modifying the input directory, or embedding the
seam marking anywhere other than `after.seams` is a contract violation
and is scored as a preservation failure.

## Held-out cases

The cases visible in this repository are examples for local development
and smoke testing. Real scoring uses hidden, held-out cases that are not
published: different meshes, different seam instructions, graded with
the same contract, the same edge indexing, and the same scoring weights
stated here. Work that only reproduces the example cases will not score
on the held-out set.
