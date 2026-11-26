# Preserve Eval — Leaderboard

Overall = 0.60 preservation + 0.25 shape + 0.15 intrinsic, public corpus. Trap entries are seeded failure patterns: a high trap score is a grader bug.

| # | Candidate | Kind | Overall | Preservation | Shape | Intrinsic | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | baseline | control | 0.9875 | 1.0 | 1.0 | 0.9167 | pass |
| 2 | lane-chatgpt | lane | 0.9875 | 1.0 | 1.0 | 0.9167 | pass |
| 3 | lane-claude | lane | 0.9875 | 1.0 | 1.0 | 0.9167 | pass |
| 4 | lane-deepseek | lane | 0.9875 | 1.0 | 1.0 | 0.9167 | pass |
| 5 | lane-gemini | lane | 0.9875 | 1.0 | 1.0 | 0.9167 | pass |
| 6 | lane-a | lane | 0.9125 | 0.875 | 1.0 | 0.9167 | fail |
| 7 | lane-b | lane | 0.9125 | 0.875 | 1.0 | 0.9167 | fail |
| 8 | traps/uv-swap | trap | 0.7125 | 0.5417 | 1.0 | 0.9167 | fail |
| 9 | traps/component-swap | trap | 0.6625 | 0.4583 | 1.0 | 0.9167 | fail |
| 10 | traps/vertex-reorder | trap | 0.5625 | 0.2916 | 1.0 | 0.9167 | fail |
| 11 | traps/axis-swap | trap | 0.503 | 0.3333 | 0.662 | 0.9167 | fail |
| 12 | sloppy | control | 0.4819 | 0.3333 | 0.5778 | 0.9167 | fail |
| 13 | traps/liar | trap | 0.0 | 0.0 | 0.0 | 0.0 | fail |
