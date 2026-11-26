#!/usr/bin/env python3
"""Phase 2 verification: the seed failure cases must actually bite.

For a given corpus dir (default corpus/, or corpus-hidden/):
  1. the baseline candidate must PASS the whole corpus;
  2. every failure case in corpus/failure-cases.json must be CAUGHT —
     its must_catch section/channel lands below the stated bound — and
     its must_not_catch section (if any) must stay at 1.0, proving the
     catch comes from the right section and not a blunt instrument.

Exit 0 = all expectations met. Prints a table.
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def grade(solver, corpus_dir, cases=None):
    """Run grader.py (optionally on a single-case sub-corpus); return summary."""
    with tempfile.TemporaryDirectory() as td:
        cdir = corpus_dir
        if cases is not None:
            cdir = os.path.join(td, "corpus")
            os.makedirs(cdir)
            full = json.load(open(os.path.join(corpus_dir, "testcases.json")))
            sub = [t for t in full["testcases"] if t["id"] in cases]
            json.dump({"testcases": sub}, open(os.path.join(cdir, "testcases.json"), "w"))
            # base paths in testcases.json are relative to the corpus dir
            for t in sub:
                src = os.path.normpath(os.path.join(corpus_dir, t["base"]))
                dst = os.path.normpath(os.path.join(cdir, t["base"]))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(src, "rb") as a, open(dst, "wb") as b:
                    b.write(a.read())
        out = os.path.join(td, "results")
        subprocess.run([sys.executable, os.path.join(ROOT, "harness", "grader.py"),
                        solver, cdir, out], capture_output=True, text=True)
        summaries = []
        for name in sorted(os.listdir(out)):
            p = os.path.join(out, name, "summary.json")
            if os.path.exists(p):
                summaries.append(json.load(open(p)))
        return summaries[0] if summaries else None


def main():
    corpus_dir = os.path.join(ROOT, sys.argv[1] if len(sys.argv) > 1 else "corpus")
    failures = json.load(open(os.path.join(ROOT, "corpus", "failure-cases.json")))["failure_cases"]
    ok = True

    base = grade(os.path.join(ROOT, "candidates", "baseline", "solve.py"), corpus_dir)
    status = "PASS" if base and base["verdict"] == "pass" else "FAIL"
    if status == "FAIL":
        ok = False
    print(f"[{'ok' if status == 'PASS' else 'XX'}] baseline full corpus: overall={base['overall'] if base else '?'} verdict={status}")

    for fc in failures:
        solver = os.path.join(ROOT, fc["trap_candidate"])
        summ = grade(solver, corpus_dir, cases={fc["case"]})
        case = next((c for c in summ["cases"] if c["id"] == fc["case"]), None)
        if case is None:
            print(f"[XX] {fc['id']}: case not graded"); ok = False; continue
        mc = fc["must_catch"]
        if mc["section"] == "overall":
            got = case["overall"]
        elif "channel" in mc:
            got = 1.0 if case["preservation_detail"]["channels_identical"][mc["channel"]] else 0.0
        else:
            got = case["sections"][mc["section"]]
        caught = got < mc["below"]
        line = f"[{'ok' if caught else 'XX'}] {fc['id']}: {mc['section']}={got} (must be < {mc['below']})"
        if "must_not_catch" in fc:
            mnc = fc["must_not_catch"]
            other = case["sections"][mnc["section"]]
            blind = other >= 0.999
            line += f" | {mnc['section']}={other} (must stay 1.0: {'ok' if blind else 'XX'})"
            caught = caught and blind
        print(line)
        ok = ok and caught
    print("PHASE2", "OK" if ok else "FAILED", f"corpus={os.path.basename(corpus_dir)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
