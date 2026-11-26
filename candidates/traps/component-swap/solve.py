"""Trap candidate 4 for preserve-eval: crossed components.

Analog of crossed/merged limbs shipping under a passing summary gate:
this solver keeps every aggregate statistic perfect while putting the
parts in the wrong places.

It finds the connected components of the base mesh (union-find over face
edges) and swaps the positions of the two largest: every vertex of
component A is translated by (centroidB - centroidA) and vice versa.
Vertex count, face structure, per-component shapes, the global unordered
vertex set, and voxel shape are all unchanged - only which component
sits where changes. Aggregate gates (counts, hashes of unordered sets,
shape IoU) all stay green; shape IoU stays 1.0. Only a per-vertex
channel diff against the base catches it.

If the mesh has fewer than 2 components there is nothing to swap: the
output is an exact copy of the input. Valid seams are impossible in
either case, so after.seams is always empty.
"""

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


def components(num_vertices, faces):
    """Connected components via union-find over face edges. Returns a
    list of vertex-index lists."""
    parent = list(range(num_vertices))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for face in faces:
        for i in range(len(face)):
            union(face[i], face[(i + 1) % len(face)])

    groups = {}
    for v in range(num_vertices):
        groups.setdefault(find(v), []).append(v)
    return list(groups.values())


def centroid(vertices, members):
    n = len(members)
    return tuple(sum(vertices[i][k] for i in members) / n for k in range(3))


def swapped_vertices(vertices, faces):
    """Vertex list with the two largest components' positions swapped.
    With fewer than 2 components, returns the vertices unchanged."""
    comps = components(len(vertices), faces)
    if len(comps) < 2:
        return vertices
    comps.sort(key=len, reverse=True)
    a_members, b_members = comps[0], comps[1]
    ca = centroid(vertices, a_members)
    cb = centroid(vertices, b_members)
    delta_ab = tuple(cb[k] - ca[k] for k in range(3))  # A -> B's place
    delta_ba = tuple(ca[k] - cb[k] for k in range(3))  # B -> A's place

    out = list(vertices)
    for i in a_members:
        out[i] = tuple(vertices[i][k] + delta_ab[k] for k in range(3))
    for i in b_members:
        out[i] = tuple(vertices[i][k] + delta_ba[k] for k in range(3))
    return out


def render(original_text, new_vertices):
    """Rebuild the OBJ text: v lines replaced with the new coordinates
    (%.6f) in original order; every other line (vt, faces, comments)
    unchanged."""
    lines = []
    v_index = 0
    for line in original_text.splitlines():
        parts = line.split()
        if parts and parts[0] == "v" and len(parts) >= 4:
            x, y, z = new_vertices[v_index]
            lines.append("v %.6f %.6f %.6f" % (x, y, z))
            v_index += 1
        else:
            lines.append(line)
    return "\n".join(lines) + "\n"


def main(argv):
    if len(argv) != 3:
        print("usage: python3 solve.py base.obj out_dir", file=sys.stderr)
        return 2
    base_path = Path(argv[1])
    out_dir = Path(argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    text = base_path.read_text(encoding="utf-8", errors="replace")
    vertices, faces = parse_obj(text)
    new_vertices = swapped_vertices(vertices, faces)
    if new_vertices is vertices or new_vertices == vertices:
        # Nothing to swap: exact copy of the input bytes.
        (out_dir / "after.obj").write_bytes(base_path.read_bytes())
    else:
        (out_dir / "after.obj").write_text(
            render(text, new_vertices), encoding="utf-8"
        )
    # No valid seam marking is produced by this trap.
    (out_dir / "after.seams").write_text("", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
