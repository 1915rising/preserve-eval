#!/usr/bin/env python3
"""preserve-eval grader (stdlib only).

Grades a candidate solver against the corpus: for each testcase it runs the
solver on the hash-pinned base OBJ, then scores the output in three sections:

  preservation (0.60) - channel hashes (vertices / faces / uvs) of after.obj
                        must equal base.obj (roundtrip-doctor idiom); the only
                        permitted change is the after.seams sidecar, which
                        must exist, be non-empty, and name valid edge indices.
  shape        (0.25) - voxel IoU of after.obj vs base.obj on a shared grid
                        (print-doctor gate_check idiom).
  intrinsic    (0.15) - standalone mesh sanity: watertight, no zero-area
                        faces, no duplicate faces (stl-doctor idiom).

Writes results/<candidate>/ per-case JSON + summary.json (doctor-chain
chain-report envelope). Exit 0 = overall >= pass_threshold, 1 = below, 2 = usage.
"""
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time

WEIGHTS = {"preservation": 0.60, "shape": 0.25, "intrinsic": 0.15}
PASS_THRESHOLD = 0.95
VOXEL_GRID = 24


def parse_obj(path):
    verts, uvs, faces = [], [], []
    with open(path) as fh:
        for line in fh:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "v":
                verts.append(tuple(float(x) for x in parts[1:4]))
            elif parts[0] == "vt":
                uvs.append(tuple(float(x) for x in parts[1:3]))
            elif parts[0] == "f":
                idx = []
                for tok in parts[1:]:
                    v = tok.split("/")[0]
                    idx.append(int(v) - 1 if int(v) > 0 else len(verts) + int(v))
                faces.append(tuple(idx))
    return verts, uvs, faces


def channel_hash(items, fmt="%.6f"):
    h = hashlib.sha256()
    for item in items:
        h.update((",".join(fmt % x for x in item) + "\n").encode())
    return h.hexdigest()


def edge_index_map(faces):
    """Edge index = order of first appearance iterating faces in file order."""
    edges = {}
    for f in faces:
        n = len(f)
        for i in range(n):
            a, b = f[i], f[(i + 1) % n]
            key = (min(a, b), max(a, b))
            if key not in edges:
                edges[key] = len(edges)
    return edges


def preservation_section(base, cand, seams_path):
    b_verts, b_uvs, b_faces = base
    c_verts, c_uvs, c_faces = cand
    channels = {
        "vertices": channel_hash(b_verts) == channel_hash(c_verts),
        "faces": channel_hash([tuple(float(x) for x in f) for f in b_faces], "%.0f")
        == channel_hash([tuple(float(x) for x in f) for f in c_faces], "%.0f"),
        "uvs": channel_hash(b_uvs) == channel_hash(c_uvs),
    }
    chan_score = sum(channels.values()) / len(channels)
    seams_ok, seams_note = False, "missing"
    if os.path.exists(seams_path):
        edges = edge_index_map(b_faces)
        try:
            idxs = [int(x) for x in open(seams_path).read().split()]
            valid = all(0 <= i < len(edges) for i in idxs)
            seams_ok = len(idxs) >= 3 and valid and len(set(idxs)) == len(idxs)
            seams_note = f"{len(idxs)} seam edges, valid={valid}"
        except ValueError:
            seams_note = "unparseable"
    score = chan_score if seams_ok else chan_score * 0.5
    return score, {"channels_identical": channels, "seams_ok": seams_ok, "seams": seams_note}


def voxel_set(verts, faces, lo, hi, grid=VOXEL_GRID):
    """Surface voxelization: sample points on every triangle into a shared grid."""
    span = [max(hi[i] - lo[i], 1e-9) for i in range(3)]

    def cell(p):
        return tuple(min(grid - 1, max(0, int((p[i] - lo[i]) / span[i] * grid))) for i in range(3))

    vox = set()
    for f in faces:
        if len(f) < 3:
            continue
        pts = [verts[i] for i in f]
        # fan-triangulate quads+
        tris = [(pts[0], pts[j], pts[j + 1]) for j in range(1, len(pts) - 1)]
        for tri in tris:
            a, b, c = tri
            steps = 12
            for i in range(steps + 1):
                for j in range(steps + 1 - i):
                    u, v = i / steps, j / steps
                    w = 1.0 - u - v
                    p = tuple(a[k] * w + b[k] * u + c[k] * v for k in range(3))
                    vox.add(cell(p))
    return vox


def shape_section(base, cand):
    b_verts, _, b_faces = base
    c_verts, _, c_faces = cand
    allv = b_verts + c_verts
    lo = [min(v[i] for v in allv) for i in range(3)]
    hi = [max(v[i] for v in allv) for i in range(3)]
    vb = voxel_set(b_verts, b_faces, lo, hi)
    vc = voxel_set(c_verts, c_faces, lo, hi)
    union = vb | vc
    iou = (len(vb & vc) / len(union)) if union else 1.0
    return iou, {"voxel_iou": round(iou, 4), "voxels_base": len(vb), "voxels_candidate": len(vc)}


def intrinsic_section(cand):
    verts, _, faces = cand
    counts = {}
    zero_area, seen, dup = 0, set(), 0
    for f in faces:
        key = tuple(sorted(f))
        if key in seen:
            dup += 1
        seen.add(key)
        n = len(f)
        for i in range(n):
            a, b = f[i], f[(i + 1) % n]
            k = (min(a, b), max(a, b))
            counts[k] = counts.get(k, 0) + 1
        if n >= 3:
            a, b, c = (verts[f[0]], verts[f[1]], verts[f[2]])
            ab = [b[i] - a[i] for i in range(3)]
            ac = [c[i] - a[i] for i in range(3)]
            cx = ab[1] * ac[2] - ab[2] * ac[1]
            cy = ab[2] * ac[0] - ab[0] * ac[2]
            cz = ab[0] * ac[1] - ab[1] * ac[0]
            if math.sqrt(cx * cx + cy * cy + cz * cz) < 1e-12:
                zero_area += 1
    boundary = sum(1 for v in counts.values() if v == 1)
    nonmanifold = sum(1 for v in counts.values() if v > 2)
    checks = {
        "watertight": boundary == 0 and nonmanifold == 0,
        "no_zero_area_faces": zero_area == 0,
        "no_duplicate_faces": dup == 0,
    }
    score = sum(checks.values()) / len(checks)
    return score, {"checks": checks, "boundary_edges": boundary,
                    "nonmanifold_edges": nonmanifold, "zero_area_faces": zero_area,
                    "duplicate_faces": dup}


def main(argv):
    if len(argv) != 4:
        print(__doc__)
        return 2
    solver_path, corpus_dir, results_dir = argv[1], argv[2], argv[3]
    with open(os.path.join(corpus_dir, "testcases.json")) as fh:
        corpus = json.load(fh)
    cand_name = os.path.splitext(os.path.basename(solver_path))[0] + "-" + os.path.basename(os.path.dirname(os.path.abspath(solver_path)))
    out_dir = os.path.join(results_dir, cand_name)
    os.makedirs(out_dir, exist_ok=True)
    started = time.time()
    cases = []
    for tc in corpus["testcases"]:
        base_path = os.path.join(corpus_dir, tc["base"])
        digest = hashlib.sha256(open(base_path, "rb").read()).hexdigest()
        if digest != tc["base_sha256"]:
            cases.append({"id": tc["id"], "error": "base hash mismatch — corpus tampered or stale"})
            continue
        with tempfile.TemporaryDirectory() as td:
            run = subprocess.run([sys.executable, solver_path, base_path, td],
                                 capture_output=True, text=True, timeout=300)
            after_obj, after_seams = os.path.join(td, "after.obj"), os.path.join(td, "after.seams")
            if run.returncode != 0 or not os.path.exists(after_obj):
                cases.append({"id": tc["id"], "error": "solver failed",
                              "stderr": run.stderr[-500:]})
                continue
            base = parse_obj(base_path)
            cand = parse_obj(after_obj)
            try:
                pres, pres_detail = preservation_section(base, cand, after_seams)
                shape, shape_detail = shape_section(base, cand)
                intr, intr_detail = intrinsic_section(cand)
            except Exception as exc:  # broken artifact = failed case, never a grader crash
                cases.append({"id": tc["id"], "sections": {"preservation": 0.0,
                              "shape": 0.0, "intrinsic": 0.0}, "overall": 0.0,
                              "error": f"ungradeable artifact: {type(exc).__name__}: {exc}"})
                with open(os.path.join(out_dir, tc["id"] + ".json"), "w") as fh:
                    json.dump(cases[-1], fh, indent=1)
                continue
        sections = {"preservation": round(pres, 4), "shape": round(shape, 4),
                    "intrinsic": round(intr, 4)}
        overall = sum(WEIGHTS[k] * sections[k] for k in WEIGHTS)
        case = {"id": tc["id"], "sections": sections, "overall": round(overall, 4),
                "preservation_detail": pres_detail, "shape_detail": shape_detail,
                "intrinsic_detail": intr_detail}
        cases.append(case)
        with open(os.path.join(out_dir, tc["id"] + ".json"), "w") as fh:
            json.dump(case, fh, indent=1)
    graded = [c for c in cases if "overall" in c]
    overall = round(sum(c["overall"] for c in graded) / len(graded), 4) if graded else 0.0
    summary = {"tool": "preserve-eval-grader", "candidate": cand_name,
               "verdict": "pass" if overall >= PASS_THRESHOLD else "fail",
               "overall": overall, "weights": WEIGHTS, "pass_threshold": PASS_THRESHOLD,
               "seconds": round(time.time() - started, 2), "cases": cases}
    with open(os.path.join(out_dir, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1)
    print(f"{cand_name}: overall={overall} verdict={summary['verdict']} "
          f"({len(graded)}/{len(cases)} cases graded) -> {out_dir}/summary.json")
    return 0 if overall >= PASS_THRESHOLD else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
