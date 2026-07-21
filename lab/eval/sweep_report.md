# Hybrid-graph clustering sweep — `CITES + α·SIMILAR` (2026-07-21)

Corpus `l2_th005_clean` — 683 papers, 2,658 citation pairs, 7,777 similarity
pairs. Leiden (RBConfiguration), resolution fixed at **1.0** across the sweep so
α is the only moving part. 3 seeds per α; table values are seed means.

Reference partitions from run 3: semantic (embedding-kNN) k=8, citation k=18,
**ARI(semantic, citation) = 0.154** on this corpus (0.166 on the th=0.08 clean
corpus — the baseline you named).

## The sweep

| α | k | ① landmark ARI | ② nameability | ③ ARI vs semantic | ARI vs citation | ④ max share | ④ singletons | ⑤ stability |
|---|---|---|---|---|---|---|---|---|
| 0 (cites only) | 21.0 | 0.452 | 0.442 | 0.141 | 0.514 | 0.17 | 10.0 | 0.691 |
| 0.1 | 8.7 | **0.566** | 0.436 | 0.181 | 0.562 | 0.19 | 1.0 | 0.626 |
| **0.25** | **8.3** | **0.507** | **0.463** | **0.249** | **0.492** | **0.20** | **1.0** | **0.643** |
| 0.5 | 7.3 | 0.372 | 0.458 | 0.339 | 0.364 | 0.27 | 1.0 | 0.661 |
| 1 | 8.0 | 0.231 | 0.509 | 0.502 | 0.219 | 0.26 | 1.0 | 0.713 |
| 2 | 9.0 | 0.184 | 0.524 | 0.616 | 0.205 | 0.18 | 1.0 | 0.842 |
| 4 | 9.0 | 0.184 | 0.529 | 0.639 | 0.193 | 0.18 | 1.0 | 0.874 |
| ∞ (similarity only) | 9.3 | 0.148 | 0.518 | 0.684 | 0.166 | 0.18 | 1.0 | 0.767 |

**How the criteria were computed**

- **① landmark coherence** — ARI between the partition restricted to the 15
  landmarks and a topical family labelling I authored: *circuits* (IOI, induction
  heads, grokking, ACDC), *features* (Toy Models, SAEs, Finding Neurons),
  *probing* (linear probes, Emergent World Reps, RepE, sentiment neuron),
  *knowledge* (ROME, KV Memories, Knowledge Neurons, MEMIT). All 15 located.
  The labelling is my judgment and is in `sweep_l2_th005_clean.json` — change it
  and the winner may change.
- **② nameability** — machine half only, across all 24 partitions: size-weighted
  fraction of a cluster's papers containing at least one of its own top-3 tf-idf
  title terms. The human half (writing a 2-4 word name from ~30 sampled papers)
  was done for the winner, below. I did not hand-name all 24 partitions.
- **③** ARI against the semantic partition. Reported next to ARI-vs-citation
  because α=∞ drives ③ to 1.0 trivially — on its own it is a degenerate target.
- **④/⑤** as stated.

## Selection, and where I had to interpret you

Criteria ③④⑤ read as bars to clear, so they filter; survivors are ranked by ①
then ②. Making ③ explicit as **ARI-semantic ≥ 0.20** (the 0.166 baseline + 20%,
i.e. "materially above") is the one judgment call, and it decides the outcome:

- **Ranking on ① alone gives α = 0.1** (landmark ARI 0.566). But its ARI-vs-semantic
  is **0.181 — only 9% above the baseline**. It fails "materially above".
- **With ③ enforced, α = 0.25 wins**: landmark ARI 0.507 (within 10% of the peak),
  ARI-semantic 0.249 (+50% over baseline), ARI-citation 0.492.

α=0.25 is also where the partition stays genuinely bound to *both* views — it has
the best balance of ARI-semantic and ARI-citation of any α that clears the bar.
Past α≈0.5 the citation graph stops mattering and you are re-deriving the semantic
partition; ① falls off a cliff (0.507 → 0.372 → 0.231) while ③ climbs, which is the
sweep's clearest signal.

**If you disagree with the ≥0.20 bar, α=0.1 is the alternative** and it is one
constant (`MIN_ARI_SEM` in `lab/sweep_hybrid.py`) plus a re-freeze.

## Winner: α = 0.25 — frozen as canonical

`run_id='hybrid_a0.25'` written to `data/graph_v3_clean` (`cluster_id`,
`subcluster_id`, `run_id` on all 683 nodes; schema untouched). Level-2
subclusters were recomputed on the same fused graph so both levels describe one
partitioning.

| cluster | n | name | |
|---|---|---|---|
| c0 | 144 | **Factual Knowledge & Editing** | ROME, Knowledge Neurons, MEMIT, tuned lens, factual recall |
| c1 | 125 | **Attribution & Feature Visualization** | LIME, Grad-CAM, IG, LRP, SHAP, network dissection, Activation Atlas |
| c2 | 117 | **Latent Representations & Safety** | Emergent World Reps, RepE, Geometry of Truth, refusal direction |
| c3 | 108 | **BERT-Era Probing** | BERT Rediscovers, control tasks, amnesic probing, GLUE |
| c4 | 99 | **Circuits & Superposition** | IOI, induction heads, grokking, Toy Models, ACDC |
| c5 | 56 | ⚠ *Sparse Autoencoders / Bio-LMs* | **resists naming** |
| c6 | 33 | ⚠ *Multimodal & Architecture Misc* | **resists naming** |
| c7 | 1 | ⚠ singleton | infant-psychology paper |

**5 of 8 name cleanly. Three do not, and I'm not dressing that up:**

- **c5** fuses two unrelated things — SAE/dictionary-learning work (SAEs, Gemma
  Scope, transcoders, InterPLM) and protein/DNA language models (ESM, ProtTrans,
  DNABERT, AlphaFold 3). Only a conjunction names it. It also splits the *features*
  family: SAEs land here while Toy Models lands in c4.
- **c6** is a grab-bag — ViT, wav2vec, speech recognition, pose estimation,
  layer-norm analysis. Nothing shared beyond "transformer-adjacent". It also
  captured KV Memories, pulling one landmark out of the knowledge family.
- **c7** is one paper.

**The useful read: c5 and c6 are corpus problems, not clustering problems.** The
bio-LM tail and the architecture/multimodal tail are pollution that survived
hygiene; the clustering is now good enough to *localize* them into two clusters
rather than smear them everywhere. That makes them cheap to attack next.

## Criterion ① in detail — where each landmark landed

| family | landing | verdict |
|---|---|---|
| circuits | IOI, induction heads, grokking, ACDC → **all c4** | clean |
| knowledge | ROME, Knowledge Neurons, MEMIT → **c0**; KV Memories → c6 | 3/4 |
| features | Toy Models, Finding Neurons → c4; SAEs → c5 | 2/3, split |
| probing | linear probes → c1, Emergent World Reps + RepE → c2, sentiment neuron → c3 | **shredded** |

Circuits is perfect. Probing is the weak spot — it scatters across three clusters,
which is most of what holds landmark ARI at 0.507 rather than higher. Arguably the
"probing" family is genuinely heterogeneous (a 2016 linear-probe paper, a 2022
world-model paper and a 2023 control paper are not one school), so this may be my
family labelling being wrong rather than the clustering.

## Artifacts

| what | where |
|---|---|
| full sweep, per-α, per-seed, all partitions | `lab/eval/sweep_l2_th005_clean.json` |
| cluster names, exemplars, top terms | `lab/eval/cluster_names_hybrid_a0.25.json` |
| annotated scatter (⚠ marks unnameable) | `lab/out/hybrid_scatter_hybrid_a0.25.html` |
| canonical graph | `data/graph_v3_clean`, `run_id='hybrid_a0.25'` |
| sweep code | `lab/sweep_hybrid.py`, `lab/freeze_clustering.py` |

```bash
python lab/sweep_hybrid.py --run-id l2_th005_clean
python lab/freeze_clustering.py --alpha 0.25 --run-id hybrid_a0.25
```

Positions in the scatter are the existing UMAP-of-embeddings layout, so it also
shows how the hybrid partition sits against pure semantic space — the clusters
are deliberately not clean blobs.
