"""lab/sweep_hybrid.py — hybrid-graph clustering sweep.

Leiden over a fused graph:  w(u,v) = CITES(u,v) + alpha * SIMILAR(u,v)
  alpha = 0    → citation graph only
  alpha = inf  → semantic kNN graph only
Resolution is held at 1.0 across the sweep so alpha is the only moving part.
3 seeds per alpha.

Criteria computed per alpha (priority order is applied in select()):
  1. landmark coherence  — ARI between the partition restricted to the 15
     landmarks and a hand-authored topical family labelling (LANDMARK_FAMILIES).
     Also reports how many distinct clusters the 12 CORE landmarks span.
  2. nameability (proxy)  — for each cluster, the top-3 tf-idf title terms; the
     score is the size-weighted fraction of a cluster's papers that contain at
     least one of its own top-3 terms. A cluster with no dominant shared
     vocabulary scores low — that is the machine-checkable half of "resists
     naming". The human half (actually writing a 2-4 word name from ~30 sampled
     papers) is done for the finalists, not for all 24 partitions.
  3. ARI vs the semantic partition (embedding-kNN Leiden from run_l2), whose
     citation-vs-semantic baseline was 0.166. ARI vs the citation partition is
     reported alongside, because alpha=inf drives criterion 3 to 1.0 trivially.
  4. shape — largest-cluster share, clusters with <5 members, singletons.
  5. stability — mean pairwise ARI across the 3 seeds at that alpha.

Usage:
  python lab/sweep_hybrid.py --run-id l2_th005_clean
"""
import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import igraph as ig
import leidenalg
import numpy as np
from sklearn.metrics import adjusted_rand_score

ROOT = Path(__file__).resolve().parent.parent
EVAL = ROOT / "lab" / "eval"

ALPHAS = [0.0, 0.1, 0.25, 0.5, 1.0, 2.0, 4.0, float("inf")]
SEEDS = [1, 2, 3]
RESOLUTION = 1.0

# Topical families for criterion 1. My judgment, stated so it can be argued with:
# a good clustering should put these together and not shred them.
LANDMARK_FAMILIES = {
    "2211.00593": "circuits",      # IOI
    "2209.11895": "circuits",      # induction heads
    "2301.05217": "circuits",      # grokking
    "2304.14997": "circuits",      # ACDC
    "2209.10652": "features",      # Toy Models of Superposition
    "2309.08600": "features",      # SAEs
    "2305.01610": "features",      # Finding Neurons in a Haystack
    "1610.01644": "probing",       # linear classifier probes
    "2210.13382": "probing",       # Emergent World Representations
    "2310.01405": "probing",       # Representation Engineering
    "1704.01444": "probing",       # sentiment neuron
    "2202.05262": "knowledge",     # ROME
    "2012.14913": "knowledge",     # FFN key-value memories
    "2104.08696": "knowledge",     # knowledge neurons
    "2210.07229": "knowledge",     # MEMIT
}

STOP = set("a an the of and or for with to in on by using via is are we our this that from as at "
           "be can do does how what when which why not but their its it new towards toward using "
           "study analysis approach method methods model models based".split())


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def build_graph(n, cite_pairs, sim_pairs, alpha):
    """Fused undirected weighted graph."""
    w = defaultdict(float)
    if alpha != float("inf"):
        for e in cite_pairs:
            w[e] += 1.0
    if alpha > 0:
        a = 1.0 if alpha == float("inf") else alpha
        for e, s in sim_pairs.items():
            w[e] += a * s
    edges = list(w)
    g = ig.Graph(n=n, edges=edges, directed=False)
    g.es["weight"] = [w[e] for e in edges]
    return g


def tfidf_names(members, titles, df, n_docs, topk=3):
    tf = Counter()
    for i in members:
        tf.update(set(norm(titles[i]).split()) - STOP)
    scored = sorted(((t, (c / len(members)) * math.log(n_docs / (1 + df[t])))
                     for t, c in tf.items() if len(t) > 2),
                    key=lambda x: -x[1])[:topk]
    terms = [t for t, _ in scored]
    if not terms:
        return [], 0.0
    hit = sum(1 for i in members if set(norm(titles[i]).split()) & set(terms))
    return terms, hit / len(members)


def evaluate(part, titles, df, n_docs, lm_idx, lm_labels, sem, cit):
    m = list(part)
    n = len(m)
    sizes = Counter(m)
    clusters = defaultdict(list)
    for i, c in enumerate(m):
        clusters[c].append(i)

    # 1 · landmark coherence
    lm_clusters = [m[i] for i in lm_idx]
    lm_ari = adjusted_rand_score(lm_labels, lm_clusters) if len(set(lm_labels)) > 1 else float("nan")
    core_span = len({m[i] for i, lab in zip(lm_idx, lm_labels)})

    # 2 · nameability proxy
    cov, tot, names = 0.0, 0, {}
    for c, mem in clusters.items():
        terms, coverage = tfidf_names(mem, titles, df, n_docs)
        names[c] = terms
        if len(mem) >= 5:
            cov += coverage * len(mem); tot += len(mem)
    nameability = cov / tot if tot else 0.0

    # 3 · agreement with the two pure views
    ari_sem = adjusted_rand_score(sem, m)
    ari_cite = adjusted_rand_score(cit, m)

    # 4 · shape
    max_share = max(sizes.values()) / n
    n_small = sum(1 for v in sizes.values() if v < 5)
    n_singleton = sum(1 for v in sizes.values() if v == 1)

    return {"k": len(sizes), "landmark_ari": lm_ari, "landmark_cluster_span": core_span,
            "nameability": nameability, "ari_semantic": ari_sem, "ari_citation": ari_cite,
            "max_cluster_share": max_share, "clusters_lt5": n_small,
            "singletons": n_singleton, "singleton_share": n_singleton / n,
            "sizes": dict(sizes), "top_terms": {str(k): v for k, v in names.items()}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="l2_th005_clean")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = [json.loads(ln) for ln in
            (ROOT / "data" / "processed" / f"interp_{args.run_id}.jsonl").read_text().splitlines()
            if ln.strip()]
    n = len(rows)
    idx = {r["id"]: i for i, r in enumerate(rows)}
    titles = [r["title"] for r in rows]
    print(f"[sweep] {n} papers from interp_{args.run_id}.jsonl")

    cite_pairs = []
    for r in rows:
        for t in r.get("edges", []):
            if t in idx and idx[t] != idx[r["id"]]:
                a, b = sorted((idx[r["id"]], idx[t]))
                cite_pairs.append((a, b))
    sim_pairs = {}
    for r in rows:
        for s in r.get("_similar", []):
            if s["target"] in idx:
                a, b = sorted((idx[r["id"]], idx[s["target"]]))
                if a != b:
                    sim_pairs[(a, b)] = max(sim_pairs.get((a, b), 0.0), float(s["weight"]))
    print(f"[sweep] {len(set(cite_pairs))} citation pairs, {len(sim_pairs)} similarity pairs")

    # reference partitions from run_l2
    sem = [r["cluster_id"] for r in rows]
    cit = [int(r["_scores"]["cite_cluster_id"]) for r in rows]
    print(f"[sweep] reference: semantic k={len(set(sem))}, citation k={len(set(cit))}, "
          f"ARI={adjusted_rand_score(sem, cit):.3f}")

    df = Counter()
    for t in titles:
        df.update(set(norm(t).split()) - STOP)

    by_ax = {r.get("arxiv_id"): i for i, r in enumerate(rows) if r.get("arxiv_id")}
    ntitles = {norm(r["title"]): i for i, r in enumerate(rows)}
    lm_idx, lm_labels, missing = [], [], []
    lmeta = json.loads((EVAL / "landmarks.json").read_text())["landmarks"]
    tier = {L["arxiv_id"]: L.get("tier", "core") for L in lmeta}
    title_of = {L["arxiv_id"]: L["title"] for L in lmeta}
    for ax, fam in LANDMARK_FAMILIES.items():
        i = by_ax.get(ax)
        if i is None:
            nt = norm(title_of.get(ax, ""))
            i = next((j for k, j in ntitles.items() if nt and (nt in k or k in nt)), None)
        if i is None:
            missing.append(ax); continue
        lm_idx.append(i); lm_labels.append(fam)
    print(f"[sweep] landmarks located: {len(lm_idx)}/{len(LANDMARK_FAMILIES)}"
          + (f" (missing {missing})" if missing else ""))

    results, partitions = [], {}
    for alpha in ALPHAS:
        g = build_graph(n, cite_pairs, sim_pairs, alpha)
        per_seed, parts = [], []
        for s in SEEDS:
            p = leidenalg.find_partition(g, leidenalg.RBConfigurationVertexPartition,
                                         weights="weight", resolution_parameter=RESOLUTION,
                                         seed=s)
            parts.append(list(p.membership))
            per_seed.append(evaluate(list(p.membership), titles, df, n, lm_idx, lm_labels, sem, cit))
        stab = float(np.mean([adjusted_rand_score(parts[i], parts[j])
                              for i in range(len(parts)) for j in range(i + 1, len(parts))]))
        agg = {"alpha": alpha, "edges": g.ecount(), "stability": stab}
        for key in ("k", "landmark_ari", "landmark_cluster_span", "nameability",
                    "ari_semantic", "ari_citation", "max_cluster_share",
                    "clusters_lt5", "singletons", "singleton_share"):
            agg[key] = float(np.mean([r[key] for r in per_seed]))
        # keep seed 1's partition as the representative for the winner
        partitions[str(alpha)] = {"membership": parts[0], "detail": per_seed[0]}
        results.append(agg)
        a = "inf" if alpha == float("inf") else alpha
        print(f"  a={str(a):<5} k={agg['k']:>5.1f} lmARI={agg['landmark_ari']:.3f} "
              f"name={agg['nameability']:.3f} ariSem={agg['ari_semantic']:.3f} "
              f"ariCit={agg['ari_citation']:.3f} max={agg['max_cluster_share']:.2f} "
              f"sing={agg['singletons']:.1f} stab={stab:.3f}")

    # ── selection ────────────────────────────────────────────────────────────
    # Criteria 3, 4 and 5 are the ones stated as bars to clear ("materially
    # above the 0.166 baseline", "no mega-cluster or singleton rain", "stable"),
    # so they act as filters; the survivors are then ranked by criterion 1 and
    # tie-broken by criterion 2, which is the stated priority order.
    # MIN_ARI_SEM makes "materially above" explicit: baseline 0.166 + 20%.
    MIN_ARI_SEM = 0.20

    def feasible(r):
        return (r["ari_semantic"] >= MIN_ARI_SEM
                and r["max_cluster_share"] <= 0.40 and r["singleton_share"] <= 0.05
                and r["stability"] >= 0.50 and 4 <= r["k"] <= 30)
    ok = [r for r in results if feasible(r)]
    pool = ok or results
    ranked = sorted(pool, key=lambda r: (-r["landmark_ari"], -r["nameability"], -r["ari_semantic"]))
    winner = ranked[0]
    print(f"\n[sweep] feasible alphas: {[('inf' if r['alpha']==float('inf') else r['alpha']) for r in ok]}")
    print(f"[sweep] WINNER alpha={winner['alpha']} "
          f"(landmark_ari={winner['landmark_ari']:.3f}, nameability={winner['nameability']:.3f}, "
          f"ari_semantic={winner['ari_semantic']:.3f})")

    out = Path(args.out) if args.out else EVAL / f"sweep_{args.run_id}.json"
    out.write_text(json.dumps({
        "run_id": args.run_id, "resolution": RESOLUTION, "seeds": SEEDS,
        "papers": n, "landmark_families": LANDMARK_FAMILIES,
        "reference": {"semantic_k": len(set(sem)), "citation_k": len(set(cit)),
                      "ari_semantic_vs_citation": adjusted_rand_score(sem, cit)},
        "results": results, "feasible": [r["alpha"] for r in ok],
        "winner": winner, "partitions": partitions,
    }, indent=2, default=str))
    print(f"→ {out}")


if __name__ == "__main__":
    main()
