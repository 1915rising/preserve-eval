"""Lane B candidate for preserve-eval.

Strategy: sharp-edge-first seam marking, exact preservation.

Preservation: after.obj is a byte-for-byte copy of base.obj, so every
parsed channel (vertex coordinates and order, face structure, UVs) is
identical to the base by construction. The seam marking lives only in
the after.seams sidecar, as the contract requires.

Seam selection: a human cutting UV seams cuts along hard edges, where
the surface bends sharply and a seam hides in the crease. So for every
edge (indexed exactly per spec/TASK.md: faces in file order, sorted
1-based vertex-index pairs, index assigned by first appearance) this
solver computes the dihedral angle between the normals of the faces
adjacent to the edge (Newell normals, so n-gon faces work) and marks
the edge as a seam when that angle is at least SHARP_THRESHOLD_DEGREES
— the conventional hard-edge cutoff. Boundary edges (a single adjacent
face) are also marked: they are the mesh's natural cut boundary.
Non-manifold edges use the largest pairwise angle between their
adjacent face normals. Degenerate (zero-area) faces contribute no
normal and are ignored for angle purposes.

Usage: python3 solve.py base.obj out_dir
Writes out_dir/after.obj and out_dir/after.seams (one integer edge
index per line, ascending, no duplicates). Pure Python 3 stdlib.
"""

import math
import os
import sys

SHARP_THRESHOLD_DEGREES = 45.0


def parse_obj(text):
    """Return (vertices, faces): vertices as (x, y, z) float tuples in
    file order; faces as lists of resolved 0-based vertex indices in
    file order. Handles f tokens of the forms v, v/vt, v/vt/vn, v//vn,
    including negative (relative) indices."""
    vertices = []
    faces = []
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v" and len(parts) >= 4:
            vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif parts[0] == "f" and len(parts) >= 4:
            face = []
            for token in parts[1:]:
                index = int(token.split("/")[0])
                face.append(index - 1 if index > 0 else len(vertices) + index)
            faces.append(face)
    return vertices, faces


def face_edges(face):
    """Edges of one face as sorted 0-based vertex-index pairs, walked in
    face order: consecutive pairs plus last-to-first."""
    edges = []
    count = len(face)
    for i in range(count):
        a, b = face[i], face[(i + 1) % count]
        edges.append((a, b) if a < b else (b, a))
    return edges


def newell_normal(vertices, face):
    """Unit normal of a (possibly n-gon) face via Newell's method.
    Returns None for a degenerate face."""
    nx = ny = nz = 0.0
    count = len(face)
    for i in range(count):
        x1, y1, z1 = vertices[face[i]]
        x2, y2, z2 = vertices[face[(i + 1) % count]]
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length == 0.0:
        return None
    return (nx / length, ny / length, nz / length)


def angle_between(n1, n2):
    """Angle in degrees between two unit normals, in [0, 180]."""
    dot = n1[0] * n2[0] + n1[1] * n2[1] + n1[2] * n2[2]
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(math.acos(dot))


def seam_edge_indices(vertices, faces):
    """Edge indices (spec indexing: first appearance across faces in
    file order) of every sharp or boundary edge."""
    edge_index = {}
    edge_faces = {}
    for face_number, face in enumerate(faces):
        for edge in face_edges(face):
            if edge not in edge_index:
                edge_index[edge] = len(edge_index)
                edge_faces[edge] = []
            edge_faces[edge].append(face_number)

    normals = [newell_normal(vertices, face) for face in faces]

    seams = []
    for edge, index in edge_index.items():
        adjacent = [normals[f] for f in edge_faces[edge]
                    if normals[f] is not None]
        if len(edge_faces[edge]) == 1:
            # Boundary edge: the mesh's natural cut boundary.
            seams.append(index)
        elif len(adjacent) >= 2:
            sharpest = 0.0
            for i in range(len(adjacent)):
                for j in range(i + 1, len(adjacent)):
                    sharpest = max(sharpest,
                                   angle_between(adjacent[i], adjacent[j]))
            if sharpest >= SHARP_THRESHOLD_DEGREES:
                seams.append(index)
    return sorted(seams)


def main(argv):
    if len(argv) != 3:
        print("usage: python3 solve.py base.obj out_dir", file=sys.stderr)
        return 2
    base_path, out_dir = argv[1], argv[2]
    os.makedirs(out_dir, exist_ok=True)

    with open(base_path, "rb") as handle:
        raw = handle.read()

    # Preservation: copy the input bytes exactly.
    with open(os.path.join(out_dir, "after.obj"), "wb") as handle:
        handle.write(raw)

    vertices, faces = parse_obj(raw.decode("utf-8", errors="replace"))
    seams = seam_edge_indices(vertices, faces)
    with open(os.path.join(out_dir, "after.seams"), "w",
              encoding="utf-8") as handle:
        handle.write("".join("%d\n" % index for index in seams))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
