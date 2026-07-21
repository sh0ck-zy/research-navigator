# ingest_v3 run 2 + L0→L2 — report (2026-07-21)

## Outcome
| gate | result | |
|---|---|---|
| (a) core landmarks | **11/12** | **FAIL** — misses only `1610.01644` (linear probes) |
| (b) purity, top-50 | **68% core** (need ≥60) | **PASS** |

Per your rule (*"run gate (b) purity at 0.08 and report — if core ≥60%, proceed to full L0→L1→L2"*)
I proceeded. Gate (a) is the one open decision, and it's a one-line fix — see §3.

---

## 1 · Seed resolution — fixed, and the bug was worse than diagnosed

**5 of 18 seeds resolved to the wrong work** (not ~3), and the root cause is *not*
a bad DOI index. OpenAlex's arXiv-DOI mapping is correct; some records have
**corrupted title/abstract metadata** — a junk source has overwritten the text
fields while authors and citation edges survive:

| DOI | OpenAlex title | actual paper (authors confirm) |
|---|---|---|
| `10.48550/arxiv.2209.10652` | "Governance Architecture for Neural Network Superposition…" | Toy Models of Superposition (Elhage, Hume, Olsson…) |
| `10.48550/arxiv.2310.01405` | "Its Alive: AI Independence Without Human Prompting" | Representation Engineering (Zou, Phan, Chen…) — *abstract is verbatim RepE* |

The fix in `ingest_v3.resolve_seed()` now does, for every seed:
1. DOI lookup → **verify title** (punctuation/case-tolerant, subtitle-tolerant) and year (±3, warn-only);
2. mismatch → **title search**, accept only verified matches, prefer the highest-cited version;
3. still nothing → the DOI record **with its title repaired from ground truth** (the arXiv DOI is a 1:1 identifier, so the record *is* the right paper), flagged `title_repaired`.

It also keeps up to 3 **alternate OpenAlex versions** of each seed (preprint vs published
records are separate works), so forward citation no longer misses citers that point at
the version we didn't pick.

Result: **18/18 correct** — 13 clean DOI, 3 rescued by title search, 2 title-repaired, 0 missing.
Audit trail: `data/raw/.ckpt_v3/seed_resolution.json`.

## 2 · Corpus (keep-threshold 0.08)

| | run 1 | run 2 |
|---|---|---|
| papers | 116 | **635** |
| candidate pool | 2,629 | **2,789** |
| in-corpus edges | 168 | **1,842** |
| ≥1 edge | 90.5% | **97.8%** |
| forward citers | 875 | 941 |

Year distribution now has a real historical tail instead of a 2023-26 spike:
`2014:3 2015:8 2016:13 2017:27 2018:43 2019:41 2020:48 2021:40 2022:51 2023:147 2024:107 2025:83 2026:24`.

## 3 · Gate (a) — 11/12, and the only fix is one number

`1610.01644` (Understanding intermediate layers using linear classifier probes)
**is in the candidate pool** with label-prop score **0.051** — below the 0.08 you set.
It is not a capture failure; it needs th ≤ 0.05.

| th | papers | edges | core landmarks | all 15 |
|----|--------|-------|----|----|
| 0.20 | 288 | 636 | 11/12 | 11/15 |
| 0.10 | 555 | 1494 | 11/12 | 11/15 |
| **0.08** | **635** | **1842** | **11/12** | 12/15 |
| 0.06 | 763 | 2551 | 11/12 | 13/15 |
| **0.05** | **878** | **3314** | **12/12 ✅** | 14/15 |
| 0.03 | 1241 | 6548 | 12/12 | 14/15 |

**Purity does not degrade at 0.05 — it improves (70% vs 68%).** Dropping to 0.05 admits
the classic probing/feature-visualization lineage (control tasks, network dissection,
object detectors in CNN units, Bau's unit-role work) faster than it admits noise.
So 0.05 passes *both* your gates. Your call — I did not change the threshold.

## 4 · Gate (b) — purity of the top-50 by in-corpus cites

| th | core | adjacent | off-topic | core % | verdict |
|----|------|----------|-----------|--------|---------|
| 0.08 | 34 | 13 | 3 | **68.0%** | PASS |
| 0.05 | 35 | 11 | 4 | **70.0%** | PASS |

Rule used (stated in the artifact so you can argue with it): **core** = mechanistic /
inner-structure interp (circuits, features, neurons, activation geometry, probing
internals, lens methods, causal localization); **adjacent** = interpretability but not
mechanistic (LIME/SHAP/IG/LRP/CAM attribution, XAI surveys, position papers, pure
model-editing methods); **off** = not interpretability (base-model releases, benchmarks,
other fields) or corrupted records. Full 100-row classification with a 1-line
justification each: `lab/eval/purity_sample.json`.

*Note:* this topical rule puts FFN Key-Value Memories and Knowledge Neurons in **core**,
while your landmark tiering has them as **adjacent**. Flagged rather than silently
reconciled — the questions differ ("is this the right field?" vs "must this paper be present?").

## 5 · L0→L2 baselines (`run_id = l2_th008`, 635 papers)

`embed` MiniLM → `similar` cosine kNN k=15, cos≥0.30 → **9,435 SIMILAR** edges →
`cluster` Leiden(res=1.0) 2-level → `centrality` 7 baselines → `layout` UMAP(seed=42) →
Kùzu (`data/graph_v3`).

### 5a · The blend is worse than its own best component

Landmark ranking is the eval (lower = better), over the 11 present core landmarks in 635 papers:

| metric | median | mean | in top-50 | worst |
|---|---|---|---|---|
| **in_corpus_cites** | **7** | **12.2** | 11/11 | 43 |
| hits_authority | 11 | 19.2 | 10 | 60 |
| pagerank | 15 | 23.9 | 10 | 85 |
| betweenness | 8 | 24.9 | 9 | 137 |
| *centrality (my provisional blend)* | 22 | 30.5 | 9 | 78 |
| recency_velocity | 160 | 160.6 | 0 | 287 |
| cited_by_count | 164 | 165.5 | 0 | 293 |
| emb_centrality | 194 | 245.3 | 2 | 603 |

Two real findings:
- **Plain in-corpus citation count beats PageRank, HITS, betweenness and my blend.** At
  n=635 with 1.8k edges the graph is too shallow for spectral methods to add signal.
- **`emb_centrality` (cosine to cluster centroid) is actively harmful** — it measures
  *typicality*, not importance, and it is what drags the blend down. It also lifts
  pollution: GLUE ranks 0.931 and ESMFold 0.922 under the blend.
- `cited_by_count` (global citations) is near-useless for ranking *within* the field —
  which is the argument for the in-corpus graph existing at all.

`PROVISIONAL_BLEND` is one dict at the top of `lab/run_l2.py`. Suggested starting point
for you: `in_corpus_cites 0.6 / hits_authority 0.25 / pagerank 0.15`, drop `emb_centrality`.

### 5b · Clustering: the two views of structure disagree

| | clusters | modularity | |
|---|---|---|---|
| embedding kNN (Leiden) | 8 | 0.514 | silhouette **0.062** |
| citation graph (Leiden) | 23 | 0.564 | |
| agreement | | | **ARI 0.104** |

The clusters are semantically legible (c6 model editing, c4 SAE/sparse features,
c3 transformer internals, c0 probing, c2 classic XAI/vision, c5 sentiment,
c7 text generation) — but **silhouette 0.062 means they barely separate in MiniLM space**,
and **ARI 0.104 means the semantic and citation communities are nearly independent**.

That's the biggest open ML question from this run, and it's yours: cluster on citations,
on embeddings, or on a fused graph? And is MiniLM-on-abstracts good enough, or is this
the moment for SPECTER2 (which is trained on citation proximity and would partly
reconcile the two views by construction)?

Clusters c5 (sentiment analysis, n=44) and c7 (controlled text generation, n=20) are
**pollution clusters** inherited from the sentiment-neuron seed's forward citations —
i.e. clustering does isolate the noise, which is useful.

## 6 · Data-quality findings (new, not yet acted on)

1. **Duplicate records: 25 groups, 3.9% of the corpus** (GLUE ×2, LIME ×2, "What you can
   cram" ×2, Analyzing Transformers ×2…). OpenAlex stores preprint and published versions
   as separate works. They split citation counts and inflate cluster sizes. A dedup stage
   (normalized title + year window, merge edges, keep highest-cited id) is worth ~4% and
   would improve every centrality metric. Not applied — it's a corpus-shape decision.
2. **Reference-magnet record.** "On a Method to Measure Supervised Multiclass Model's
   Interpretability: Application to Degradation Diagnosis" (industrial maintenance,
   Dagstuhl) ranks **top-10 by in-corpus cites** with `cited_by_count=13417`. The title
   is genuine; the *citation edges* are corrupt — OpenAlex has mis-resolved dozens of
   references onto this work id. It survives the keyword prior because its title contains
   "interpretability". No automatic rule applied.
3. **Off-domain venues:** bioRxiv 15, Qeios 9, medRxiv 1 (of 635). Minor; Qeios entries
   are mostly arXiv mirrors of real interp papers.
4. **Corrupted abstracts poison embeddings — visible downstream.** The title repair (§1)
   fixes identity but not the *text*. Toy Models of Superposition still carries the junk
   abstract ("…hallucination is a structural consequence of ungoverned superposition, a
   governance filter on the Gram matrix…"), so its MiniLM vector is garbage: it lands in
   c2 (classic XAI/vision) instead of c4 (SAE/features), and its nearest neighbours are
   **Voyager (an embodied-agent paper) at cos 0.456**. RepE, by contrast, kept a genuine
   abstract and its neighbours are correct (Toward Transparent AI, 0.731).
   Fix: for `title_repaired` records, pull title+abstract from the **arXiv API** instead
   of OpenAlex (OpenAlex stays the citation-edge source). Cheap — 2 records today, and it
   generalizes to any record we detect as corrupt.

## 7 · Decisions waiting for you

1. **Threshold** — stay at 0.08 (635 papers, 11/12) or go 0.05 (878 papers, **12/12**,
   purity 70%)? 0.05 satisfies both your gates. One command re-runs everything.
2. **Centrality blend** — `PROVISIONAL_BLEND` in `lab/run_l2.py`. Numbers say drop
   `emb_centrality` and weight `in_corpus_cites` heaviest.
3. **Clustering basis** — embeddings (ARI 0.10 vs citations, silhouette 0.06),
   citations, or fused? SPECTER2 now or later?
4. **Dedup** — apply the 3.9% dedup stage?
5. **Magnet record + pollution clusters** — filter, or leave visible as honest noise?
6. **arXiv fallback for text** — fetch title+abstract from arXiv for corrupted records
   (§6.4)? Recommended: it's a correctness fix of the same family as the seed bug, and
   right now one of your most important landmarks has a nonsense embedding.

## 8 · Artifacts (all saved)

| what | where |
|---|---|
| corpus, th=0.08 | `data/raw/interp_corpus_v3.jsonl` (635) |
| corpus, run 1 (archived) | `data/raw/interp_corpus_v3_run1.jsonl` (116) |
| seed resolution audit | `data/raw/.ckpt_v3/seed_resolution.json` |
| checkpoints (re-runnable) | `data/raw/.ckpt_v3/{seeds,candidates}.json` |
| enriched corpus (all computed fields) | `data/processed/interp_l2_th008.jsonl` |
| embeddings | `data/embeddings/interp_l2_th008.npz` |
| graph (Kùzu) | `data/graph_v3/` — `run_id='l2_th008'` |
| gate (a) report | `lab/eval/ingest_report.json` |
| gate (b) purity, 100 rows classified | `lab/eval/purity_sample.json` |
| L2 stats + eval | `lab/eval/l2_stats_l2_th008.json`, `lab/eval/l2_report_l2_th008.json` |
| logs | `data/raw/ingest_v3_run2.log`, `lab/eval/l2_run.log` |
| dev viewer | `lab/out/l2_scatter.html`, `lab/out/l2_graph.html` |

Re-run everything at a different threshold:

```bash
rm -rf data/raw/.ckpt_v3/candidates.json          # keep seeds.json (resolution is fixed)
.venv/bin/python backend/pipeline/ingest_v3.py --mailto <you> --keep-threshold 0.05
.venv/bin/python lab/eval/report.py --corpus data/raw/interp_corpus_v3.jsonl
.venv/bin/python lab/run_l2.py --run-id l2_th005 --db data/graph_v3_005
.venv/bin/python lab/eval/l2_report.py --run-id l2_th005
```
