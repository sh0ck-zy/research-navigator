# Run 3 — hygiene + threshold 0.05 + re-measure (2026-07-21)

Your four decisions, executed. Gates both pass. **Stopping here** — the
hybrid-graph clustering experiment is yours.

| gate | run 2 (poisoned, th=0.08) | **run 3 (clean, th=0.05)** |
|---|---|---|
| (a) core landmarks | 11/12 FAIL | **12/12 PASS** (adjacent 3/3 too) |
| (b) purity, top-50 | 68% | **62% PASS** |
| papers | 635 | **683** |
| in-corpus edges | 1,842 | **2,663** |
| ≥1 edge | 97.8% | **98.5%** |

---

## 1 · What the hygiene stage removed (`lab/hygiene.py`, all auditable)

New stage between capture and filtering. Nothing is dropped silently — every
removal is in `lab/eval/quarantine.json` with a reason.

| step | effect |
|---|---|
| arXiv text repair | **775 records** now take title+abstract from arXiv; **67 had a corrupted title** |
| corrupt metadata | 24 quarantined ('Untitled', Dagstuhl/DROPS container records) |
| reference magnets | 3 quarantined |
| single-seed forward | **351 quarantined** (sentiment-neuron-only citers) |
| dedup | **152 duplicate records merged** |
| | **530 quarantined, 3,754 kept** |

Two things I had to fix mid-run, both worth knowing:

**(i) My first repair rule was wrong.** I detected corruption by title mismatch —
but `ingest_v3` had already repaired seed *titles* from ground truth, so the title
agreed while the abstract stayed corrupt. Toy Models of Superposition sailed
through with its junk abstract. Fixed by treating arXiv as authoritative for the
*text* of any arXiv paper (OpenAlex remains the sole source of citation edges),
and by resolving arXiv ids from the DataCite DOI as well as the landing page —
which took coverage from 729 to 745 records and repaired 775 in total.
Toy Models now reads *"Neural networks often pack many unrelated concepts into a
single neuron — a puzzling phenomenon known as 'polysemanticity'…"*

**(ii) Dedup recovered a lot of edges.** Merging duplicate records and remapping
their references onto canonical ids took the candidate-pool edge count from
**30,260 → 56,640**. Many references that previously dangled onto a duplicate id
now resolve. This is why in-corpus edges rose (1,842 → 2,663) even though the
corpus only grew 635 → 683.

## 2 · A measurement bug in gate (b) — found because of (ii)

`ingest_v3` writes `_in_corpus_cites`, but it counts citations within the whole
**candidate pool** (2,351), not within the final corpus. `lab/eval/report.py` was
ranking the purity sample by that number. GLUE showed 97 — its real in-corpus
in-degree is **19**.

The effect is exactly what you'd expect: generic ML background is heavily cited
across the pool but barely inside the corpus, so pool-ranking made the purity
sample look far more polluted than the corpus is.

**Same corpus, two rankings: 56% core (pool-ranked) vs 62% core (corpus-ranked).**
Fixed — `report.py` now ranks by true in-corpus in-degree, and the field is
renamed `in_pool_cites` so it can't be confused again. Runs 1 and 2 were scored
on the buggy ranking; their 68%/70% numbers are not comparable to this 62%.

## 3 · ARI, measured properly

You were right not to conclude from 0.104. Poisoned embeddings *were* part of it —
but only part. Controlled comparison, **same threshold, same everything except hygiene**:

| | clusters | modularity | citation communities | **ARI** | silhouette |
|---|---|---|---|---|---|
| th=0.08 poisoned (run 2) | 8 | 0.514 | 23 (0.564) | **0.104** | 0.062 |
| th=0.08 **clean** | 9 | 0.478 | 22 (0.539) | **0.166** | 0.067 |
| th=0.05 **clean** (main) | 8 | 0.512 | 18 (0.523) | **0.154** | 0.060 |

**ARI 0.104 → 0.166 at matched threshold — a 60% relative lift from hygiene alone.**
Silhouette barely moved (0.062 → 0.067).

So: the poison was real and worth removing, and the disagreement is still real.
At ARI ~0.16, semantic similarity and citation communities remain substantially
independent views of this field. That's now a clean number to build the
hybrid-graph experiment on rather than an artifact.

Silhouette ~0.06 is the other standing signal: MiniLM-on-abstracts barely
separates these clusters at all, whatever the graph says.

## 4 · Centrality, on the clean graph

`Paper.centrality` is now `in_corpus_cites`, raw, per your call. All 7 candidates
stay in `Paper.scores` — `emb_centrality` included. One constant at the top of
`lab/run_l2.py` (`OFFICIAL_CENTRALITY`, `NORMALIZE_CENTRALITY`).

Landmark ranking on the clean corpus (683 papers, 12 core landmarks):

| metric | median | mean | in top-50 |
|---|---|---|---|
| **in_corpus_cites** (= centrality) | 14 | **48.2** | 9/12 |
| pagerank | 31 | 52.6 | 8 |
| betweenness | **9** | 54.1 | 9 |
| hits_authority | 47 | 57.2 | 8 |
| cited_by_count | 244 | 235.7 | 0 |
| recency_velocity | 240 | 239.7 | 0 |
| emb_centrality | 240 | 269.5 | 1 |

`in_corpus_cites` still wins on mean, and the ordering is unchanged from run 2 —
your call holds on clean data. Two caveats:

- **Betweenness has the best median (9) but a worse mean (54.1)** — it ranks the
  bulk of landmarks higher but exiles a couple. If you ever blend, that's the
  complementary signal to in-degree, not PageRank.
- **All means got worse than run 2 (12.2 → 48.2)** and it's almost entirely two
  papers: the sentiment neuron fell to **rank 231** and linear probes to **151**.
  The sentiment neuron fell *because you quarantined its forward expansion* — with
  the sentiment-analysis tail gone it has 3 in-corpus citers. That's the trade you
  chose, and it's defensible (it's a 2017 ancestor, not a hub of this field), but
  it does mean a core landmark now ranks near the bottom. Worth a decision.

## 5 · Clusters after cleaning

8 clusters. c1 knowledge editing / factual localization (128), c3 classic
XAI/explainability (95), c5 BERT-era probing (70), c0 deep-network attribution and
vision (141), c4 transformers/attention/memory (81), c2 LLM behaviour and bias (107).

The sentiment and text-generation pollution clusters from run 2 are **gone**.

New artifact of `centrality = in_corpus_cites`: **LLaMA tops c4 and Llama 2 tops c2**.
Model releases win in-degree inside their clusters. If the map labels clusters by
their top-centrality paper, two of eight clusters will be named after model
releases. Fixable at label time (rank by centrality among core-classified papers)
rather than by changing the metric.

## 6 · Where things stand

- Graph: `data/graph_v3_clean/` — **683 Paper, 2,663 CITES, 10,165 SIMILAR**,
  `run_id='l2_th005_clean'`, canonical columns populated, 7 score candidates each.
- Viewer: regenerate with
  `python lab/viz.py --db data/graph_v3_clean --prefix clean_`
- Run 2's graph is untouched at `data/graph_v3/` (`run_id='l2_th008'`) for comparison.

**Open, yours:** the hybrid-graph clustering experiment (CITES + weighted SIMILAR,
multi-relation Leiden) — the ARI 0.154/0.166 baseline is what it has to beat.
Plus the sentiment-neuron ranking question in §4.

## 7 · Reproduce

```bash
python lab/hygiene.py --quarantine-seed 1704.01444
python backend/pipeline/ingest_v3.py --candidates data/raw/.ckpt_v3/candidates_clean.json \
    --keep-threshold 0.05 --out data/raw/interp_corpus_v3_clean.jsonl
python lab/eval/report.py --corpus data/raw/interp_corpus_v3_clean.jsonl
python lab/run_l2.py --corpus data/raw/interp_corpus_v3_clean.jsonl \
    --db data/graph_v3_clean --run-id l2_th005_clean
python lab/eval/l2_report.py --run-id l2_th005_clean
```
