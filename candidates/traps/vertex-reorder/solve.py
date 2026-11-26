"""TRAP 1 -- 'summary stats identical, internal order changed'.

Reverses the vertex order of the input OBJ and remaps every face index
accordingly. The geometry as an unordered set is identical: vertex/face
counts, bounding box, and shape are all unchanged, so this trap passes
any gate that only checks counts, bounds, or shape. A channel-hash
preservation grader must catch it, because the vertices channel (and the
faces channel, via the remapped indices) no longer matches the base in
its recorded order.

after.seams deliberately carries a seam set computed under the ORIGINAL
vertex indexing, so the indices are wrong under the new order -- part of
the trap: a seams file that was valid for the base silently points at
different edges after a reorder.
"""

import sys
from pathlib import Path


def parse_obj(text):
    """Return (v_lines, vt_lines, other_lines_in_order, faces).

    Kept deliberately simple: we preserve the original line strings so
    coordinates are never reformatted, only reordered / remapped.
    faces: list of faces, each a list of token strings as written.
    """
    v_lines = []
    faces = []
    lines = text.splitlines()
    for line in lines:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v":
            v_lines.append(line)
        elif parts[0] == "f":
            faces.append(parts[1:])
    return v_lines, faces, lines


def vertex_coords(v_lines):
    coords = []
    for line in v_lines:
        parts = line.split()
        coords.append((float(parts[1]), float(parts[2]), float(parts[3])))
    return coords


def face_vertex_indices(faces, nverts):
    """Faces as lists of 0-based vertex indices, in file order."""
    out = []
    for face in faces:
        idx = []
        for token in face:
            v = int(token.split("/")[0])
            idx.append(v - 1 if v > 0 else nverts + v)
        out.append(idx)
    return out


def face_edges(face):
    """Edges of one face as sorted vertex-index pairs, in face order."""
    edges = []
    count = len(face)
    for i in range(count):
        a, b = face[i], face[(i + 1) % count]
        edges.append((a, b) if a < b else (b, a))
    return edges


def min_z_seam_indices(coords, faces_idx):
    """Edge indices (order of first appearance across all faces, in file
    order) of every edge whose endpoints both sit at the minimum z level,
    computed under the ORIGINAL indexing."""
    if not coords or not faces_idx:
        return []
    min_z = min(c[2] for c in coords)
    at_min = {i for i, c in enumerate(coords) if c[2] == min_z}
    edge_index = {}
    for face in faces_idx:
        for edge in face_edges(face):
            if edge not in edge_index:
                edge_index[edge] = len(edge_index)
    return sorted(
        edge_index[edge]
        for edge in edge_index
        if edge[0] in at_min and edge[1] in at_min
    )


def remap_token(token, nverts):
    """Remap the vertex component of one face token under vertex-order
    reversal; vt/vn components are carried through unchanged."""
    parts = token.split("/")
    v = int(parts[0])
    idx0 = v - 1 if v > 0 else nverts + v
    new_v = nverts - idx0  # 1-based index of the same vertex after reversal
    parts[0] = str(new_v)
    return "/".join(parts)


def main(argv):
    if len(argv) != 3:
        print("usage: python3 solve.py base.obj out_dir", file=sys.stderr)
        return 2
    base_path = Path(argv[1])
    out_dir = Path(argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    text = base_path.read_bytes().decode("utf-8", errors="replace")
    v_lines, face_tokens, lines = parse_obj(text)
    nverts = len(v_lines)
    coords = vertex_coords(v_lines)
    faces_idx = face_vertex_indices(face_tokens, nverts)

    # Seam set under the ORIGINAL indexing (wrong after the reorder).
    seams = min_z_seam_indices(coords, faces_idx)

    reversed_v = list(reversed(v_lines))
    v_pos = 0
    face_pos = 0
    out_lines = []
    for line in lines:
        parts = line.split()
        if parts and parts[0] == "v":
            out_lines.append(reversed_v[v_pos])
            v_pos += 1
        elif parts and parts[0] == "f":
            tokens = face_tokens[face_pos]
            face_pos += 1
            out_lines.append("f " + " ".join(remap_token(t, nverts) for t in tokens))
        else:
            out_lines.append(line)
    (out_dir / "after.obj").write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    (out_dir / "after.seams").write_text(
        "".join(f"{i}\n" for i in seams), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
