# ingest_v3 — Run 1 report (2026-07-21)

## Outcome: STOPPED — hard gate (a) FAILED at default threshold
- **Gate (a) landmark checklist: 11/15** (need 15/15) → per protocol, stopped before gate (b) and L0→L2.
- Gate (b) purity: **not evaluated** (blocked by gate a).

## The corpus (default keep-threshold 0.34)
- **116 papers**, 168 in-corpus edges, 90.5% with ≥1 edge.
- Years: peak 2023 (33) / 2024 (28) / 2025 (21) / 2026 (11) — recency skew (forward-citation bias).
- Ceiling: the candidate pool is **2,629** hygienic papers (max attainable this run).

## Key finding: capture is HEALTHY — the filter is the problem
- The 2,629 candidates form a **dense** graph: **30,260 in-corpus edges (avg 11.5/paper), ~0 isolated**. Earlier "sparse graph" read was wrong (it looked at the kept-116 subset).
- **All 15 landmarks ARE in the candidate pool.** They were filtered out, not missed.
- The label-propagation keep-threshold **0.34 is too aggressive → 116 papers**.

## Calibration (real numbers) — corpus size vs keep-threshold
keep = (seed OR strong-keyword OR label-prop score ≥ th)

| th | papers | landmarks |
|----|--------|-----------|
| 0.34 | 116 | 11/15 |
| 0.30 | 130 | 11/15 |
| 0.25 | 162 | 11/15 |
| 0.20 | 276 | 12/15 |
| 0.15 | 416 | 12/15 |
| 0.10 | 523 | 12/15 |
| 0.08 | 592 | 13/15 |
| 0.05 | **816** | **15/15** |
| 0.02 | 1452 | 15/15 |

The 4 missing at 0.34 are **foundational-adjacent** (low label-prop score despite high citations — their neighbourhoods are broad, not interp-core):
- `2012.14913` FFN Key-Value Memories — score 0.205, icc 6
- `2210.07229` Mass-Editing Memory (MEMIT) — score 0.091, icc 38
- `2104.08696` Knowledge Neurons — score 0.066, icc 32
- `1610.01644` Linear classifier probes — score 0.052, icc 8

## Two real issues to fix (your call — ML/data territory)
1. **Seed resolution is unreliable.** ~3/17 seeds mis-resolved via `filter=doi:10.48550/arxiv.{id}` to WRONG works (e.g. `2310.01405` → "Its Alive: AI Independence", not "Representation Engineering"; `2209.10652` → "Governance Architecture…", not "Toy Models of Superposition"). The real papers still entered the corpus via citations, but forward-citation ran off some wrong seeds. Fix options: verify resolved title/year, or resolve arXiv→OpenAlex by title match.
2. **Forward starved (875 citers) → ceiling 2,629.** OpenAlex under-indexes citations of arXiv-only records. To reach 3–6k: more seeds (30–50 iconic), a 2nd forward hop, or accept ~2.6k for v0.

## Proposed definitive thresholds (from real numbers) — you fix these
- **keep-threshold = 0.05** → 816 papers, 15/15 landmarks. (Or keep 0.34 and trim the landmark list to the 11 interp-core, dropping the 4 editing/probing-adjacent.)
- **Gate (a):** decide whether the 4 adjacent papers are truly "must-have landmarks" or belong to an "adjacent" tier.
- **Gate (b) purity:** evaluate top-50 at the chosen threshold before committing (0.05 admits more adjacent → purity risk).
- **Forward expansion:** raise seed count and/or add hop-2 forward to lift the 2,629 ceiling.

## Decision to resume
Pick a keep-threshold (0.05 for 15/15) ± the seed/forward fixes, and I run gate (b) + full L0→L1→L2 with baselines. One line resumes it.

## Artifacts saved
- `data/raw/interp_corpus_v3.jsonl` (116) · `data/raw/ingest_v3.log`
- `data/raw/.ckpt_v3/{seeds.json, candidates.json}` (re-runnable checkpoints)
- `lab/eval/ingest_report.json` (stats + landmark report + top-50) · `lab/eval/landmarks.json`
- Code: `backend/pipeline/ingest_v3.py`, `lab/{schema.cypher, load_graph.py, viz.py, eval/report.py}`
- Plumbing validated end-to-end on the disposable corpus (run B): `lab/out/{scatter,graph}.html`, `data/graph/` (Kùzu, run_id='plumbing_test')
