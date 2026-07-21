"""lab/run_l2.py — L1/L2 baselines over the interp corpus, end to end.

Every stage here is a BASELINE with a slot to swap. The point is that one command
regenerates the whole thing, every intermediate is saved, and the eval prints
numbers you can compare across runs (everything is tagged with --run-id).

  embed      MiniLM (all-MiniLM-L6-v2) on "title. abstract"   → data/embeddings/
  similar    cosine kNN (k)                                    → SIMILAR edges
  cluster    Leiden on the embedding-kNN graph, 2 levels       → cluster_id/subcluster_id
             (+ Leiden on the CITES graph, computed for comparison only)
  centrality in-corpus cites · PageRank · betweenness · HITS authority ·
             embedding-centrality (to cluster centroid) · recency velocity
             → all stored in Paper.scores; the PROVISIONAL blend below is
               promoted to the Paper.centrality column
  layout     UMAP (fixed seed)                                 → layout_x/layout_y

Then the whole thing is loaded into Kùzu via the verified lab/schema.cypher.

Usage:
  python lab/run_l2.py --corpus data/raw/interp_corpus_v3.jsonl \
      --db data/graph_v3 --run-id l2_th008 --k 15 --resolution 1.0
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import igraph as ig
import leidenalg
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

# ── the OFFICIAL blend promoted to Paper.centrality ──────────────────────────
# PROVISIONAL — percentile-rank blend, deliberately simple and yours to change.
# Weights must sum to 1. Each component is percentile-ranked within the corpus
# first, so no single heavy-tailed metric dominates.
PROVISIONAL_BLEND = {
    "pagerank": 0.50,
    "in_corpus_cites": 0.35,
    "emb_centrality": 0.15,
}


def pct_rank(vals):
    """Percentile rank in [0,1]; ties share the average rank."""
    a = np.asarray(vals, dtype=float)
    order = a.argsort()
    ranks = np.empty(len(a), dtype=float)
    ranks[order] = np.arange(len(a), dtype=float)
    # average ties
    out = np.zeros(len(a))
    for v in np.unique(a):
        m = a == v
        out[m] = ranks[m].mean()
    return out / max(len(a) - 1, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="data/raw/interp_corpus_v3.jsonl")
    ap.add_argument("--db", default="data/graph_v3")
    ap.add_argument("--run-id", default="l2_th008")
    ap.add_argument("--k", type=int, default=15, help="kNN neighbours for SIMILAR + clustering")
    ap.add_argument("--resolution", type=float, default=1.0, help="Leiden resolution, level 1")
    ap.add_argument("--sub-resolution", type=float, default=1.5, help="Leiden resolution, level 2")
    ap.add_argument("--model", default="all-MiniLM-L6-v2")
    ap.add_argument("--sim-min", type=float, default=0.30, help="drop kNN edges below this cosine")
    ap.add_argument("--skip-load", action="store_true")
    args = ap.parse_args()

    corpus = ROOT / args.corpus if not Path(args.corpus).is_absolute() else Path(args.corpus)
    papers = [json.loads(ln) for ln in corpus.read_text().splitlines() if ln.strip()]
    n = len(papers)
    idx = {p["id"]: i for i, p in enumerate(papers)}
    print(f"[l2] corpus {corpus.name}: {n} papers")

    # ── embed ────────────────────────────────────────────────────────────────
    emb_path = ROOT / "data" / "embeddings" / f"interp_{args.run_id}.npz"
    if emb_path.exists():
        X = np.load(emb_path)["embeddings"]
        print(f"[embed] cache hit {X.shape}")
    else:
        from sentence_transformers import SentenceTransformer
        texts = [f"{p['title']}. {p.get('abstract') or ''}" for p in papers]
        X = np.asarray(SentenceTransformer(args.model).encode(
            texts, batch_size=64, show_progress_bar=True))
        emb_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(emb_path, embeddings=X, ids=np.array([p["id"] for p in papers]))
        print(f"[embed] {X.shape} → {emb_path}")
    Xn = X / np.linalg.norm(X, axis=1, keepdims=True)

    # ── similarity: cosine kNN ───────────────────────────────────────────────
    from sklearn.neighbors import NearestNeighbors
    k = min(args.k + 1, n)
    nn = NearestNeighbors(n_neighbors=k, metric="cosine").fit(Xn)
    dist, ind = nn.kneighbors(Xn)
    sim_edges, und = [], set()
    for i in range(n):
        for d, j in zip(dist[i][1:], ind[i][1:]):
            w = 1.0 - float(d)
            if w >= args.sim_min:
                sim_edges.append((i, int(j), w))
                und.add((min(i, int(j)), max(i, int(j))))
    print(f"[similar] {len(sim_edges)} directed kNN edges (k={args.k}, cos>={args.sim_min}), "
          f"{len(und)} undirected")

    # ── cluster: Leiden on the embedding-kNN graph, 2 levels ─────────────────
    gsim = ig.Graph(n=n, edges=sorted(und), directed=False)
    part = leidenalg.find_partition(gsim, leidenalg.RBConfigurationVertexPartition,
                                    resolution_parameter=args.resolution, seed=42)
    cluster_id = list(part.membership)
    mod_emb = gsim.modularity(cluster_id)
    sub_id = [0] * n
    for cid in sorted(set(cluster_id)):
        members = [i for i in range(n) if cluster_id[i] == cid]
        if len(members) < 8:
            continue
        sub = gsim.subgraph(members)
        sp = leidenalg.find_partition(sub, leidenalg.RBConfigurationVertexPartition,
                                      resolution_parameter=args.sub_resolution, seed=42)
        for local, m in enumerate(members):
            sub_id[m] = sp.membership[local]
    n_clusters = len(set(cluster_id))
    print(f"[cluster] {n_clusters} clusters (Leiden res={args.resolution}), "
          f"modularity={mod_emb:.3f}, sizes={Counter(cluster_id).most_common(8)}")

    # citation-graph clustering, for comparison only (not written to the db)
    cite_edges = [(idx[p["id"]], idx[t]) for p in papers for t in p.get("edges", []) if t in idx]
    gcite = ig.Graph(n=n, edges=cite_edges, directed=True)
    gcite_u = gcite.as_undirected(mode="collapse")
    cpart = leidenalg.find_partition(gcite_u, leidenalg.RBConfigurationVertexPartition,
                                     resolution_parameter=args.resolution, seed=42)
    cite_clusters = list(cpart.membership)
    from sklearn.metrics import adjusted_rand_score, silhouette_score
    ari = adjusted_rand_score(cluster_id, cite_clusters)
    sil = float(silhouette_score(Xn, cluster_id, metric="cosine")) if n_clusters > 1 else float("nan")
    print(f"[cluster] citation-graph Leiden: {len(set(cite_clusters))} clusters, "
          f"modularity={gcite_u.modularity(cite_clusters):.3f} | ARI(emb,cites)={ari:.3f} | "
          f"silhouette(emb)={sil:.3f}")

    # ── centrality baselines on the CITES graph ──────────────────────────────
    icc = np.zeros(n)
    for a, b in cite_edges:
        icc[b] += 1
    pagerank = np.asarray(gcite.pagerank(damping=0.85))
    betweenness = np.asarray(gcite_u.betweenness())
    hits_auth = np.asarray(gcite.hub_score()) if gcite.ecount() else np.zeros(n)
    try:
        hits_auth = np.asarray(gcite.authority_score())
    except Exception:
        pass
    # embedding centrality: cosine to own-cluster centroid
    emb_cent = np.zeros(n)
    for cid in set(cluster_id):
        m = np.array([i for i in range(n) if cluster_id[i] == cid])
        c = Xn[m].mean(axis=0)
        c /= (np.linalg.norm(c) or 1.0)
        emb_cent[m] = Xn[m] @ c
    years = np.array([p.get("year") or 2020 for p in papers], dtype=float)
    cbc = np.array([p.get("cited_by_count") or 0 for p in papers], dtype=float)
    recency_velocity = cbc / np.clip(2027.0 - years, 1, None)

    metrics = {
        "in_corpus_cites": icc, "pagerank": pagerank, "betweenness": betweenness,
        "hits_authority": hits_auth, "emb_centrality": emb_cent,
        "recency_velocity": recency_velocity, "cited_by_count": cbc,
    }
    ranks = {k2: pct_rank(v) for k2, v in metrics.items()}
    centrality = sum(w * ranks[k2] for k2, w in PROVISIONAL_BLEND.items())
    print(f"[centrality] blend={PROVISIONAL_BLEND} → centrality in "
          f"[{centrality.min():.3f}, {centrality.max():.3f}]")

    # ── layout: UMAP ─────────────────────────────────────────────────────────
    import umap
    xy = umap.UMAP(n_neighbors=min(15, n - 1), min_dist=0.1, metric="cosine",
                   random_state=42).fit_transform(Xn)
    xy = np.asarray(xy, dtype=float)
    print(f"[layout] UMAP → x[{xy[:,0].min():.1f},{xy[:,0].max():.1f}] "
          f"y[{xy[:,1].min():.1f},{xy[:,1].max():.1f}]")

    # ── attach everything to the corpus rows ─────────────────────────────────
    sim_by_src = defaultdict(list)
    for i, j, w in sim_edges:
        sim_by_src[i].append({"target": papers[j]["id"], "weight": round(w, 4),
                              "metric": "cosine_knn", "model": args.model})
    for i, p in enumerate(papers):
        p["cluster_id"] = int(cluster_id[i])
        p["subcluster_id"] = int(sub_id[i])
        p["layout_x"] = float(xy[i, 0])
        p["layout_y"] = float(xy[i, 1])
        p["centrality"] = float(centrality[i])
        p["_scores"] = {m: float(v[i]) for m, v in metrics.items()}
        p["_scores"]["cite_cluster_id"] = float(cite_clusters[i])
        p["_similar"] = sim_by_src[i]

    enriched = ROOT / "data" / "processed" / f"interp_{args.run_id}.jsonl"
    enriched.parent.mkdir(parents=True, exist_ok=True)
    with enriched.open("w") as f:
        for p in papers:
            f.write(json.dumps(p) + "\n")
    print(f"[save] enriched corpus → {enriched}")

    stats = {
        "run_id": args.run_id, "corpus": str(corpus), "papers": n,
        "params": {"k": args.k, "resolution": args.resolution,
                   "sub_resolution": args.sub_resolution, "model": args.model,
                   "sim_min": args.sim_min},
        "similar_edges": len(sim_edges), "cite_edges": len(cite_edges),
        "clusters": n_clusters, "modularity_embedding_knn": mod_emb,
        "modularity_citation": gcite_u.modularity(cite_clusters),
        "citation_clusters": len(set(cite_clusters)),
        "ari_embedding_vs_citation": ari, "silhouette_embedding": sil,
        "blend": PROVISIONAL_BLEND,
        "cluster_sizes": dict(Counter(cluster_id)),
    }
    (ROOT / "lab" / "eval" / f"l2_stats_{args.run_id}.json").write_text(json.dumps(stats, indent=2))

    # ── load into Kùzu ───────────────────────────────────────────────────────
    if not args.skip_load:
        import load_graph
        load_graph.load(run_id=args.run_id, reset=True,
                        corpus=str(enriched), db_path=str(ROOT / args.db))


if __name__ == "__main__":
    main()
