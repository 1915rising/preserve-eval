"""Sloppy candidate for preserve-eval (negative control).

Role: the candidate that SHOULD fail. It performs an unrequested,
geometry-changing edit — every vertex z is scaled by 1.05 — and marks no
seams at all (empty after.seams). If the preservation / shape grading is
working, this candidate scores badly; if it passes, the grader is broken.
"""

import sys
from pathlib import Path


def scale_obj(text):
    """Return the OBJ text with every vertex z scaled by 1.05 (floats
    reformatted); all other lines, including faces, are preserved."""
    out_lines = []
    for line in text.splitlines():
        parts = line.split()
        if parts and parts[0] == "v" and len(parts) >= 4:
            x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
            rest = " " + " ".join(parts[4:]) if len(parts) > 4 else ""
            out_lines.append(f"v {x:.6f} {y:.6f} {z * 1.05:.6f}{rest}")
        else:
            out_lines.append(line)
    result = "\n".join(out_lines)
    if text.endswith("\n"):
        result += "\n"
    return result


def main(argv):
    if len(argv) != 3:
        print("usage: python3 solve.py base.obj out_dir", file=sys.stderr)
        return 2
    base_path = Path(argv[1])
    out_dir = Path(argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    text = base_path.read_text(encoding="utf-8", errors="replace")
    (out_dir / "after.obj").write_text(scale_obj(text), encoding="utf-8")
    (out_dir / "after.seams").write_text("", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
