"""TRAP 3 -- 'appearance channel wrong, geometry untouched'.

Writes after.obj byte-identical to the base EXCEPT that every vt line
has its u and v components swapped. Vertex positions, vertex order,
faces and counts are untouched, so geometry gates and the shape section
must pass; only the uvs channel hash can catch it.

This is the analog of a build whose geometry and texture files all check
out, yet whose rendered appearance is wrong because the wrong channel
data feeds the output -- a failure that file-exists and geometry gates
structurally cannot see.

If the OBJ has no vt lines there is no UV channel to corrupt: the file
is written unchanged and the trap instead relies on after.seams being
empty (no valid seam set is produced). When vt lines are present, a
valid seam set (minimum-z-level edges, original indexing) is written so
the UV swap is the ONLY defect.
"""

import sys
from pathlib import Path


def seam_indices(lines):
    """Valid seam set: edge indices (order of first appearance across all
    faces, in file order) of edges whose endpoints both sit at the
    minimum z level."""
    coords = []
    faces = []
    for line in lines:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v" and len(parts) >= 4:
            coords.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif parts[0] == "f":
            face = []
            for token in parts[1:]:
                v = int(token.split("/")[0])
                face.append(v - 1 if v > 0 else len(coords) + v)
            faces.append(face)
    if not coords or not faces:
        return []
    min_z = min(c[2] for c in coords)
    at_min = {i for i, c in enumerate(coords) if c[2] == min_z}
    edge_index = {}
    for face in faces:
        count = len(face)
        for i in range(count):
            a, b = face[i], face[(i + 1) % count]
            edge = (a, b) if a < b else (b, a)
            if edge not in edge_index:
                edge_index[edge] = len(edge_index)
    return sorted(
        edge_index[e] for e in edge_index if e[0] in at_min and e[1] in at_min
    )


def main(argv):
    if len(argv) != 3:
        print("usage: python3 solve.py base.obj out_dir", file=sys.stderr)
        return 2
    base_path = Path(argv[1])
    out_dir = Path(argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = base_path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()

    has_vt = any(line.split()[:1] == ["vt"] for line in lines)
    if has_vt:
        out_lines = []
        for line in lines:
            parts = line.split()
            if parts and parts[0] == "vt" and len(parts) >= 3:
                # Swap the u and v tokens textually; any further
                # components (w) and the original formatting of the
                # numbers themselves are preserved.
                parts[1], parts[2] = parts[2], parts[1]
                out_lines.append(" ".join(parts))
            else:
                out_lines.append(line)
        (out_dir / "after.obj").write_text("\n".join(out_lines) + "\n", encoding="utf-8")
        seams = seam_indices(lines)
        (out_dir / "after.seams").write_text(
            "".join(f"{i}\n" for i in seams), encoding="utf-8"
        )
    else:
        (out_dir / "after.obj").write_bytes(raw)
        (out_dir / "after.seams").write_text("", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
