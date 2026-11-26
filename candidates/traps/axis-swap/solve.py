"""TRAP 2 -- 'axis convention error'.

Writes after.obj with the y and z coordinates of every vertex swapped
(vt lines and faces carried through unchanged). This models the classic
wrong-axis-convention failure: the file is well-formed, counts and
topology are perfect, but the mesh stands in the wrong frame. Both the
preservation section (vertices channel hash) and the shape section
(voxel IoU against the base) must drop. after.seams is empty.
"""

import sys
from pathlib import Path


def main(argv):
    if len(argv) != 3:
        print("usage: python3 solve.py base.obj out_dir", file=sys.stderr)
        return 2
    base_path = Path(argv[1])
    out_dir = Path(argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    text = base_path.read_bytes().decode("utf-8", errors="replace")
    out_lines = []
    for line in text.splitlines():
        parts = line.split()
        if parts and parts[0] == "v" and len(parts) >= 4:
            x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
            out_lines.append("v %.6f %.6f %.6f" % (x, z, y))
        else:
            out_lines.append(line)
    (out_dir / "after.obj").write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    (out_dir / "after.seams").write_text("", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
