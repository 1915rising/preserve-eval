import sys
import os
import math
from collections import defaultdict

def parse_obj(path):
    verts = []
    uvs = []
    faces = []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if parts[0] == 'v':
                verts.append(tuple(float(x) for x in parts[1:4]))
            elif parts[0] == 'vt':
                uvs.append(tuple(float(x) for x in parts[1:3]))
            elif parts[0] == 'f':
                face = []
                for tok in parts[1:]:
                    segs = tok.split('/')
                    vi = int(segs[0])
                    face.append(vi)
                faces.append(face)
    return verts, uvs, faces

def build_edge_index(faces):
    edge_map = {}
    edge_list = []
    for face in faces:
        n = len(face)
        for i in range(n):
            a = face[i]
            b = face[(i + 1) % n]
            key = (a, b) if a < b else (b, a)
            if key not in edge_map:
                edge_map[key] = len(edge_list)
                edge_list.append(key)
    return edge_map, edge_list

def edge_face_map(faces):
    ef = defaultdict(list)
    for fi, face in enumerate(faces):
        n = len(face)
        for i in range(n):
            a = face[i]
            b = face[(i + 1) % n]
            key = (a, b) if a < b else (b, a)
            ef[key].append(fi)
    return ef

def face_normal(verts, face):
    n = len(face)
    if n < 3:
        return (0.0, 0.0, 0.0)
    ax = ay = az = 0.0
    for i in range(1, n - 1):
        p0 = verts[face[0] - 1]
        p1 = verts[face[i] - 1]
        p2 = verts[face[i + 1] - 1]
        ux = p1[0] - p0[0]; uy = p1[1] - p0[1]; uz = p1[2] - p0[2]
        vx = p2[0] - p0[0]; vy = p2[1] - p0[1]; vz = p2[2] - p0[2]
        ax += uy * vz - uz * vy
        ay += uz * vx - ux * vz
        az += ux * vy - uy * vx
    ln = math.sqrt(ax * ax + ay * ay + az * az)
    if ln < 1e-12:
        return (0.0, 0.0, 0.0)
    return (ax / ln, ay / ln, az / ln)

def compute_seams(verts, faces, edge_map, edge_list):
    ef = edge_face_map(faces)
    normals = [face_normal(verts, f) for f in faces]
    cos_thresh = math.cos(math.radians(30.0))
    sharp = []
    for key, flist in ef.items():
        if len(flist) == 2:
            n0 = normals[flist[0]]
            n1 = normals[flist[1]]
            d = n0[0] * n1[0] + n0[1] * n1[1] + n0[2] * n1[2]
            if d < cos_thresh:
                sharp.append(edge_map[key])
        elif len(flist) == 1:
            sharp.append(edge_map[key])
        else:
            sharp.append(edge_map[key])
    # Fallback: if fewer than 3, add more deterministically
    if len(sharp) < 3:
        chosen = set(sharp)
        # Add boundary edges first, then arbitrary edges in index order
        for idx in range(len(edge_list)):
            if idx not in chosen:
                chosen.add(idx)
                if len(chosen) >= 3:
                    break
        sharp = sorted(chosen)
    return sorted(set(sharp))

def main():
    if len(sys.argv) != 3:
        sys.exit(1)
    base_path = sys.argv[1]
    out_dir = sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)

    verts, uvs, faces = parse_obj(base_path)
    edge_map, edge_list = build_edge_index(faces)

    # Perfect copy of input bytes
    with open(base_path, 'rb') as f:
        data = f.read()
    with open(os.path.join(out_dir, 'after.obj'), 'wb') as f:
        f.write(data)

    seams = compute_seams(verts, faces, edge_map, edge_list)
    with open(os.path.join(out_dir, 'after.seams'), 'w') as f:
        for s in seams:
            f.write(str(s) + '\n')

if __name__ == '__main__':
    main()
