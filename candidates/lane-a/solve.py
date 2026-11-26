"""Lane A candidate for preserve-eval.

Strategy (geometry-first, spec-only):
  1. Parse the OBJ properly: vertex positions and face vertex indices
     (handling plain, v/vt, v/vt/vn and negative-index face tokens).
  2. Preserve identity the strongest way available: after.obj is an
     exact byte copy of base.obj, so vertex coordinates, vertex order,
     face structure and UVs cannot drift, reorder, or reformat.
  3. Build the edge index exactly as the contract defines it: faces in
     file order, consecutive vertex pairs plus the closing pair, each
     edge an unordered sorted pair of 1-based vertex indices, indexed
     by first appearance starting at 0.
  4. Choose the seam set as a real closed loop, not a scatter: for each
     coordinate axis and each distinct vertex level on that axis, take
     the edges whose endpoints both lie at that level and look for a
     connected component in which every vertex has degree 2 -- a true
     cycle lying in a constant-coordinate plane. Among all such loops,
     prefer the one whose level sits closest to the middle of the mesh
     along its axis (a seam around the mesh's equator), breaking ties
     toward the longer loop. If leaf-pruning a level's edge set reveals
     a cycle, that cycle is used. If no closed loop exists at any
     level, after.seams is left empty, which the contract allows.
"""

import sys
from pathlib import Path


def parse_obj(text):
    """Return (vertices, faces): vertices as (x, y, z) float tuples and
    faces as lists of resolved 1-based vertex indices, in file order."""
    vertices = []
    faces = []
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v" and len(parts) >= 4:
            vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif parts[0] == "f" and len(parts) >= 2:
            face = []
            for token in parts[1:]:
                index = int(token.split("/")[0])
                if index < 0:
                    index = len(vertices) + index + 1
                face.append(index)
            if len(face) >= 3:
                faces.append(face)
    return vertices, faces


def build_edge_index(faces):
    """Map each sorted 1-based vertex-index pair to its edge index,
    assigned by first appearance across faces in file order."""
    edge_index = {}
    for face in faces:
        count = len(face)
        for i in range(count):
            a, b = face[i], face[(i + 1) % count]
            edge = (a, b) if a < b else (b, a)
            if edge not in edge_index:
                edge_index[edge] = len(edge_index)
    return edge_index


def cycles_in(edge_set):
    """Yield each closed loop in an undirected edge set, as a list of
    edges in traversal order. Leaf vertices are pruned first, so what
    remains is a disjoint union of cycles; every component that is a
    simple cycle (all degrees 2, at least 3 edges) is yielded."""
    adjacency = {}
    for a, b in edge_set:
        adjacency.setdefault(a, []).append(b)
        adjacency.setdefault(b, []).append(a)

    # Prune leaves iteratively: vertices of degree < 2 cannot be on a cycle.
    degree = {v: len(ns) for v, ns in adjacency.items()}
    stack = [v for v, d in degree.items() if d < 2]
    removed = set()
    while stack:
        v = stack.pop()
        if v in removed:
            continue
        removed.add(v)
        for n in adjacency.get(v, []):
            if n not in removed:
                degree[n] -= 1
                if degree[n] < 2:
                    stack.append(n)

    live = {
        (a, b)
        for (a, b) in edge_set
        if a not in removed and b not in removed
    }
    live_adj = {}
    for a, b in live:
        live_adj.setdefault(a, []).append(b)
        live_adj.setdefault(b, []).append(a)
    for neighbours in live_adj.values():
        neighbours.sort()

    seen_vertices = set()
    for start in sorted(live_adj):
        if start in seen_vertices:
            continue
        # Walk one component.
        component = []
        prev, current = None, start
        while True:
            component.append(current)
            seen_vertices.add(current)
            neighbours = live_adj.get(current, [])
            if len(neighbours) != 2:
                component = None
                break
            nxt = neighbours[0] if neighbours[1] == prev else neighbours[1]
            prev, current = current, nxt
            if current == start:
                break
            if current in seen_vertices and current != start:
                component = None
                break
        if component and len(component) >= 3:
            loop = []
            n = len(component)
            for i in range(n):
                a, b = component[i], component[(i + 1) % n]
                loop.append((a, b) if a < b else (b, a))
            yield loop


def choose_seam_loop(vertices, edge_index):
    """Return a list of edge indices forming one closed loop at a
    constant coordinate level, or [] if no such loop exists."""
    if not vertices:
        return []
    mins = [min(v[i] for v in vertices) for i in range(3)]
    maxs = [max(v[i] for v in vertices) for i in range(3)]
    diag = max(maxs[i] - mins[i] for i in range(3)) or 1.0
    tol = 1e-6 * diag

    edges = list(edge_index.keys())
    best = None  # (sort_key, [edge indices in loop order])

    for axis in range(3):
        span = maxs[axis] - mins[axis]
        if span <= 0:
            continue
        # Cluster the distinct vertex levels along this axis.
        levels = sorted({round(v[axis], 9) for v in vertices})
        clusters = []
        for level in levels:
            if clusters and level - clusters[-1][-1] <= tol:
                clusters[-1].append(level)
            else:
                clusters.append([level])
        for cluster in clusters:
            centre = sum(cluster) / len(cluster)
            at_level = {
                i + 1
                for i, v in enumerate(vertices)
                if abs(v[axis] - centre) <= tol
            }
            if len(at_level) < 3:
                continue
            level_edges = [e for e in edges if e[0] in at_level and e[1] in at_level]
            if len(level_edges) < 3:
                continue
            position = (centre - mins[axis]) / span  # 0..1 along the axis
            middle_distance = abs(position - 0.5)
            for loop in cycles_in(level_edges):
                # Prefer: closest to the middle of the mesh, then longest.
                key = (middle_distance, -len(loop), axis)
                if best is None or key < best[0]:
                    indices = [edge_index[e] for e in loop]
                    best = (key, indices)
    return best[1] if best else []


def main(argv):
    if len(argv) != 3:
        print("usage: python3 solve.py base.obj out_dir", file=sys.stderr)
        return 2
    base_path = Path(argv[1])
    out_dir = Path(argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = base_path.read_bytes()
    # Identity: exact copy, so no parsed channel can change.
    (out_dir / "after.obj").write_bytes(raw)

    vertices, faces = parse_obj(raw.decode("utf-8", errors="replace"))
    edge_index = build_edge_index(faces)
    seam_indices = choose_seam_loop(vertices, edge_index)

    (out_dir / "after.seams").write_text(
        "".join(f"{index}\n" for index in seam_indices), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
