"""Baseline candidate for preserve-eval.

Role: the deliberately do-almost-nothing reference solver. It copies the
input OBJ byte-for-byte (perfect preservation / shape score) and marks a
simple seam loop: the mesh's "equator", i.e. every edge whose endpoints
both lie near the median vertex height (z). It exists as the sanity /
worked-example candidate a fresh clone can grade end-to-end.
"""

import statistics
import sys
from pathlib import Path


def parse_obj(text):
    """Return (vertices, faces): vertices as (x, y, z) floats, faces as
    lists of 0-based vertex indices, in file order."""
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
                # OBJ indices are 1-based; negative indices are relative
                # to the vertices defined so far.
                face.append(index - 1 if index > 0 else len(vertices) + index)
            faces.append(face)
    return vertices, faces


def face_edges(face):
    """Edges of one face as sorted vertex-index pairs, in face order:
    (a,b),(b,c),(c,a) for triangles; (a,b),(b,c),(c,d),(d,a) for quads."""
    edges = []
    count = len(face)
    for i in range(count):
        a, b = face[i], face[(i + 1) % count]
        edges.append((a, b) if a < b else (b, a))
    return edges


def seam_edge_indices(vertices, faces):
    """Edge indices (order of first appearance across all faces, in file
    order) of every edge whose endpoints are both in the near-median-z set:
    vertices whose z is within 5% of the z-range of the median z."""
    if not vertices or not faces:
        return []
    zs = [v[2] for v in vertices]
    median_z = statistics.median(zs)
    # Snap to the actual vertex z-level closest to the median (ties go to
    # the lower level): a flat 5%-of-range band around the median contains
    # no vertices at all on meshes whose verts sit on discrete levels
    # (e.g. a cube, z in {-1, 1}, median 0).
    level = min(set(zs), key=lambda z: (abs(z - median_z), z))
    near_median = {i for i, z in enumerate(zs) if z == level}

    edge_index = {}
    for face in faces:
        for edge in face_edges(face):
            if edge not in edge_index:
                edge_index[edge] = len(edge_index)

    return sorted(
        edge_index[edge]
        for edge in edge_index
        if edge[0] in near_median and edge[1] in near_median
    )


def main(argv):
    if len(argv) != 3:
        print("usage: python3 solve.py base.obj out_dir", file=sys.stderr)
        return 2
    base_path = Path(argv[1])
    out_dir = Path(argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = base_path.read_bytes()
    # Exact copy of the input file bytes.
    (out_dir / "after.obj").write_bytes(raw)

    vertices, faces = parse_obj(raw.decode("utf-8", errors="replace"))
    seams = seam_edge_indices(vertices, faces)
    (out_dir / "after.seams").write_text(
        "".join(f"{index}\n" for index in seams), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
