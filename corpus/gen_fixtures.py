#!/usr/bin/env python3
"""Generate the preserve-eval corpus fixtures (stdlib only).

Creates three base OBJ meshes in reference/ and corpus/testcases.json with
SHA-256 pins. Fixtures are generic test geometry: a UV-mapped cube, an
icosphere (no UVs), and an open-top box (deliberately NOT watertight, so the
intrinsic section has something real to report).
"""
import hashlib
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "..", "reference")


def write_obj(name, verts, faces, uvs=None, face_uvs=None):
    path = os.path.join(REF, name)
    with open(path, "w") as fh:
        fh.write(f"# preserve-eval fixture {name}\n")
        for v in verts:
            fh.write("v %.6f %.6f %.6f\n" % v)
        if uvs:
            for uv in uvs:
                fh.write("vt %.6f %.6f\n" % uv)
        for i, f in enumerate(faces):
            if face_uvs:
                toks = [f"{v + 1}/{face_uvs[i][j] + 1}" for j, v in enumerate(f)]
            else:
                toks = [str(v + 1) for v in f]
            fh.write("f " + " ".join(toks) + "\n")
    return path


def cube():
    v = [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
         (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]
    f = [(0, 1, 2, 3), (5, 4, 7, 6), (4, 0, 3, 7), (1, 5, 6, 2),
         (3, 2, 6, 7), (4, 5, 1, 0)]
    uv = [(0, 0), (1, 0), (1, 1), (0, 1)]
    fuv = [(0, 1, 2, 3)] * 6
    return v, f, uv, fuv


def icosphere(subdiv=2):
    t = (1.0 + math.sqrt(5.0)) / 2.0
    verts = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0),
             (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
             (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
             (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
             (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
             (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]

    def norm(v):
        n = math.sqrt(sum(x * x for x in v))
        return tuple(x / n for x in v)

    verts = [norm(v) for v in verts]
    for _ in range(subdiv):
        cache, new_faces = {}, []
        def mid(a, b):
            key = (min(a, b), max(a, b))
            if key not in cache:
                m = norm(tuple((verts[a][i] + verts[b][i]) / 2 for i in range(3)))
                verts.append(m)
                cache[key] = len(verts) - 1
            return cache[key]
        for a, b, c in faces:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            new_faces += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        faces = new_faces
    return verts, faces, None, None


def two_components():
    # two separate unit cubes, centred at x=-2 and x=+2: the 'limbs' fixture
    v0, f0, _, _ = cube()
    verts, faces = [], []
    for dx in (-2.0, 2.0):
        off = len(verts)
        verts += [(x * 0.5 + dx, y * 0.5, z * 0.5) for (x, y, z) in v0]
        faces += [tuple(i + off for i in f) for f in f0]
    return verts, faces, None, None


def open_box():
    # cube missing its top face -> boundary edges, not watertight
    v, f, _, _ = cube()
    return v, f[:5], None, None


def main():
    os.makedirs(REF, exist_ok=True)
    cases = []
    for case_id, name, builder, desc in [
        ("cube-uv", "cube.obj", cube, "UV-mapped cube, watertight, quad faces"),
        ("icosphere", "icosphere.obj", icosphere, "Subdivided icosphere, watertight, no UVs"),
        ("open-box", "open-box.obj", open_box, "Cube missing its top face — not watertight by design"),
        ("two-components", "two-components.obj", two_components, "Two separate cubes — the crossed-components fixture"),
    ]:
        verts, faces, uvs, fuv = builder()
        path = write_obj(name, verts, faces, uvs, fuv)
        digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
        cases.append({"id": case_id, "base": f"../reference/{name}",
                      "base_sha256": digest, "description": desc})
    with open(os.path.join(HERE, "testcases.json"), "w") as fh:
        json.dump({"_comment": "preserve-eval corpus manifest; bases are hash-pinned, filenames do not matter",
                   "testcases": cases}, fh, indent=1)
    print(f"wrote {len(cases)} fixtures + testcases.json")


if __name__ == "__main__":
    main()
