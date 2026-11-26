#!/usr/bin/env python3
import sys
import os
import math
import shutil


def parse(path):
    verts = []
    faces = []
    with open(path, "r", errors="replace") as f:
        for line in f:
            s = line.strip()
            if not s or s[0] == "#":
                continue
            parts = s.split()
            tag = parts[0]
            if tag == "v" and len(parts) >= 4:
                try:
                    verts.append((float(parts[1]), float(parts[2]), float(parts[3])))
                except ValueError:
                    verts.append((0.0, 0.0, 0.0))
            elif tag == "f" and len(parts) >= 4:
                idx = []
                ok = True
                for tok in parts[1:]:
                    t = tok.split("/")[0]
                    try:
                        i = int(t)
                    except ValueError:
                        ok = False
                        break

                    if i < 0:
                        i = len(verts) + 1 + i
                    idx.append(i)
                if ok:
                    faces.append(idx)
    return verts, faces


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def norm(a):
    return math.sqrt(dot(a, a))


def face_normal(verts, f):
    # Newell's method
    nx = ny = nz = 0.0
    n = len(f)
    for i in range(n):
        a = f[i]

        b = f[(i + 1) % n]
        if a < 1 or a > len(verts) or b < 1 or b > len(verts):
            return (0.0, 0.0, 0.0)
        p = verts[a - 1]
        q = verts[b - 1]
        nx += (p[1] - q[1]) * (p[2] + q[2])
        ny += (p[2] - q[2]) * (p[0] + q[0])
        nz += (p[0] - q[0]) * (p[1] + q[1])
    l = math.sqrt(nx * nx + ny * ny + nz * nz)
    if l < 1e-20:
        return (0.0, 0.0, 0.0)
    return (nx / l, ny / l, nz / l)


def main():
    if len(sys.argv) < 3:
        print("usage: solve.py base.obj out_dir")
        sys.exit(1)
    src = sys.argv[1]
    out_dir = sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)

    shutil.copyfile(src, os.path.join(out_dir, "after.obj"))

    seams = []
    try:
        verts, faces = parse(src)

        edge_index = {}
        edge_faces = {}
        order = []
        for fi, f in enumerate(faces):

            n = len(f)
            for i in range(n):
                a = f[i]
                b = f[(i + 1) % n]
                key = (a, b) if a < b else (b, a)
                if key not in edge_index:
                    edge_index[key] = len(order)
                    order.append(key)
                    edge_faces[key] = []
                edge_faces[key].append(fi)

        total = len(order)
        normals = [face_normal(verts, f) for f in faces]

        scored = []  # (angle, idx)
        boundary = []
        for key in order:
            fl = edge_faces[key]
            idx = edge_index[key]
            if len(fl) == 1:
                boundary.append(idx)
            elif len(fl) >= 2:
                n1 = normals[fl[0]]
                n2 = normals[fl[1]]
                d = max(-1.0, min(1.0, dot(n1, n2)))
                scored.append((math.degrees(math.acos(d)), idx))

        chosen = set()
        # sharp edges
        for ang, idx in scored:
            if ang >= 60.0:
                chosen.add(idx)

        # cap to a modest fraction to avoid over-seaming
        if total > 0 and len(chosen) > max(3, total // 4):
            top = sorted(scored, key=lambda t: -t[0])[:max(3, total // 4)]
            chosen = set(i for a, i in top if a >= 60.0)

        # fallback: ensure at least 3
        if len(chosen) < 3:
            for ang, idx in sorted(scored, key=lambda t: -t[0]):
                if len(chosen) >= 3:
                    break
                chosen.add(idx)
        if len(chosen) < 3:
            for idx in boundary:
                if len(chosen) >= 3:
                    break
                chosen.add(idx)
        if len(chosen) < 3:
            for idx in range(total):
                if len(chosen) >= 3:
                    break
                chosen.add(idx)

        seams = sorted(chosen)
    except Exception:
        seams = []

    with open(os.path.join(out_dir, "after.seams"), "w") as f:
        for s in seams:
            f.write("%d\n" % s)


if __name__ == "__main__":

    main()
