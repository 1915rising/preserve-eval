#!/usr/bin/env python3
"""Generate the hidden held-out variant corpus into corpus-hidden/.

Same fixture families as the public corpus, transformed (uniform scale,
translation, and for the icosphere a different subdivision level) so a
candidate that memorised the public fixtures — or a trap tuned to them —
meets geometry it has never seen. corpus-hidden/ is gitignored: held-out
means held out. Grading expectations are identical to the public corpus.
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_fixtures as gf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIDDEN = os.path.join(ROOT, "corpus-hidden")
REF = os.path.join(HIDDEN, "reference")


def transform(verts, scale, offset):
    return [tuple(v[i] * scale + offset[i] for i in range(3)) for v in verts]


def main():
    os.makedirs(REF, exist_ok=True)
    gf.REF = REF  # write_obj targets the hidden reference dir
    cases = []
    specs = [
        ("cube-uv", "cube.obj", gf.cube, 1.7, (0.3, -0.2, 0.1)),
        ("icosphere", "icosphere.obj", lambda: gf.icosphere(1), 0.6, (-0.1, 0.4, 0.0)),
        ("open-box", "open-box.obj", gf.open_box, 2.3, (0.0, 0.0, -0.5)),
        ("two-components", "two-components.obj", gf.two_components, 1.3, (0.2, 0.2, 0.2)),
    ]
    for case_id, name, builder, scale, offset in specs:
        verts, faces, uvs, fuv = builder()
        verts = transform(verts, scale, offset)
        path = gf.write_obj(name, verts, faces, uvs, fuv)
        digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
        cases.append({"id": case_id, "base": f"reference/{name}",
                      "base_sha256": digest,
                      "description": "hidden variant — transformed fixture"})
    with open(os.path.join(HIDDEN, "testcases.json"), "w") as fh:
        json.dump({"_comment": "hidden held-out variants; do not commit",
                   "testcases": cases}, fh, indent=1)
    print(f"wrote {len(cases)} hidden variants -> {HIDDEN}")


if __name__ == "__main__":
    main()
