"""Trap candidate 5 for preserve-eval: the process says PASS, the
artifact says otherwise.

Analog of a runner that self-reports success - the editor closes, the
exit code is 0, the log says PASS - while its state file / shipped
artifact is actually failed. A grader must read artifacts, never the
solver's exit code or self-report.

This solver writes a deliberately broken artifact (after.obj is the
base with its LAST vertex line removed and its faces left unchanged, so
face indices now point past the end of the vertex list), an empty
after.seams, and a summary.json claiming a perfect score - then prints
PASS and exits 0. Every self-report channel says success; only grading
the artifact itself reveals the truth.
"""

import json
import sys
from pathlib import Path


def remove_last_vertex_line(text):
    """Return the OBJ text with the last 'v ' line removed. All other
    lines (vt, faces, comments) are left unchanged."""
    lines = text.splitlines()
    last_v = None
    for i, line in enumerate(lines):
        parts = line.split()
        if parts and parts[0] == "v" and len(parts) >= 4:
            last_v = i
    if last_v is not None:
        del lines[last_v]
    return "\n".join(lines) + "\n"


def main(argv):
    if len(argv) != 3:
        print("usage: python3 solve.py base.obj out_dir", file=sys.stderr)
        return 2
    base_path = Path(argv[1])
    out_dir = Path(argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    text = base_path.read_text(encoding="utf-8", errors="replace")
    (out_dir / "after.obj").write_text(
        remove_last_vertex_line(text), encoding="utf-8"
    )
    (out_dir / "after.seams").write_text("", encoding="utf-8")
    # The lie: a self-report claiming a perfect run.
    (out_dir / "summary.json").write_text(
        json.dumps({"overall": 1.0, "verdict": "pass"}, indent=1) + "\n",
        encoding="utf-8",
    )
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
