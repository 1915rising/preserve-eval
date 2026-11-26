#!/usr/bin/env python3
"""Build the preserve-eval leaderboard.

Grades every candidate solver found under candidates/ (baseline, lane-*,
traps/*, sloppy) against the public corpus, then aggregates the per-case
summaries into leaderboard.json + LEADERBOARD.md:

  - overall + per-section means per candidate
  - trajectory: cumulative mean overall after each case (the checkpoint
    series, in corpus order) — scores here are non-monotonic by design,
    exactly as in long-horizon evals
  - wall-clock seconds per grading run and the solver's SHA-256, so an
    entry is tied to the exact code that produced it

Trap candidates are leaderboard entries too, flagged kind="trap": a trap
scoring high would be a grader bug, and the board should say so in public.
"""
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_solvers():
    out = []
    cand = os.path.join(ROOT, "candidates")
    for dirpath, _dirs, files in os.walk(cand):
        if "solve.py" in files:
            rel = os.path.relpath(dirpath, cand)
            kind = "trap" if rel.startswith("traps") else ("control" if rel in ("baseline", "sloppy") else "lane")
            out.append((rel.replace(os.sep, "/"), kind, os.path.join(dirpath, "solve.py")))
    return sorted(out)


def main():
    corpus = os.path.join(ROOT, "corpus")
    results = os.path.join(ROOT, "results")
    entries = []
    for name, kind, solver in find_solvers():
        subprocess.run([sys.executable, os.path.join(ROOT, "harness", "grader.py"),
                        solver, corpus, results], capture_output=True, text=True)
        # locate this solver's summary (grader names it solve-<parent dir>)
        parent = os.path.basename(os.path.dirname(solver))
        summary_path = os.path.join(results, f"solve-{parent}", "summary.json")
        if not os.path.exists(summary_path):
            print(f"!! {name}: no summary produced"); continue
        summ = json.load(open(summary_path))
        graded = [c for c in summ["cases"] if "sections" in c]
        sections = {}
        for sec in ("preservation", "shape", "intrinsic"):
            sections[sec] = round(sum(c["sections"][sec] for c in graded) / len(graded), 4) if graded else 0.0
        trajectory, run = [], 0.0
        for i, c in enumerate(graded):
            run += c["overall"]
            trajectory.append({"checkpoint": i + 1, "case": c["id"],
                               "cumulative_overall": round(run / (i + 1), 4)})
        entries.append({"candidate": name, "kind": kind,
                        "solver_sha256": hashlib.sha256(open(solver, "rb").read()).hexdigest(),
                        "overall": summ["overall"], "verdict": summ["verdict"],
                        "sections": sections, "wall_clock_seconds": summ["seconds"],
                        "trajectory": trajectory})
        print(f"{name:28s} kind={kind:7s} overall={summ['overall']}")
    entries.sort(key=lambda e: -e["overall"])
    board = {"eval": "preserve-eval", "corpus_cases": len(json.load(open(os.path.join(corpus, "testcases.json")))["testcases"]),
             "weights": {"preservation": 0.60, "shape": 0.25, "intrinsic": 0.15},
             "entries": entries}
    with open(os.path.join(ROOT, "leaderboard.json"), "w") as fh:
        json.dump(board, fh, indent=1)
    lines = ["# Preserve Eval — Leaderboard", "",
             "Overall = 0.60 preservation + 0.25 shape + 0.15 intrinsic, public corpus. "
             "Trap entries are seeded failure patterns: a high trap score is a grader bug.", "",
             "| # | Candidate | Kind | Overall | Preservation | Shape | Intrinsic | Verdict |",
             "|---|---|---|---|---|---|---|---|"]
    for i, e in enumerate(entries, 1):
        s = e["sections"]
        lines.append(f"| {i} | {e['candidate']} | {e['kind']} | {e['overall']} | "
                     f"{s['preservation']} | {s['shape']} | {s['intrinsic']} | {e['verdict']} |")
    with open(os.path.join(ROOT, "LEADERBOARD.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"leaderboard: {len(entries)} entries -> leaderboard.json + LEADERBOARD.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
