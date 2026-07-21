"""lab/layout_hybrid.py — recompute the LAYOUT from the hybrid graph.

The clustering is frozen (alpha=0.25 hybrid). The old layout came from UMAP over
MiniLM embeddings, so positions encoded semantics while colours encoded the
hybrid partition — two different metrics on one canvas. This recomputes
coordinates from the SAME fused graph the clusters came from.

Methods:
  n2v  random walks over the weighted fused graph -> PPMI co-occurrence ->
       truncated SVD to 32d -> UMAP to 2d. This is DeepWalk/node2vec(p=q=1) in
       its matrix-factorisation form: same objective, no gensim dependency, and
       fully deterministic for a fixed seed.
  drl  igraph DrL (the OpenOrd family), weighted, fixed seed.

Both are scored on whether territories actually read spatially:
  knn_purity  mean fraction of each point's 10 nearest 2D neighbours that share
              its cluster (1.0 = perfectly separated territories)
  silhouette  silhouette of the cluster labels in 2D euclidean space

Clustering, names and colours are untouched.

Usage:
  python lab/layout_hybrid.py --alpha 0.25 --method n2v --run-id hybrid_a0.25_n2v
"""
import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import igraph as ig
import kuzu
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import silhouette_score
from sklearn.neighbors import NearestNeighbors

ROOT = Path(__file__).resolve().parent.parent
EVAL = ROOT / "lab" / "eval"
OUT = ROOT / "lab" / "out"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from freeze_clustering import NAMES  # noqa: E402  (names/colours stay as frozen)

PALETTE = ["#4C9BE8", "#E8734C", "#5FC27E", "#C878E0", "#E8C64C",
           "#4CD3E8", "#E85C8A", "#9AA6B2", "#8A7CE0"]


def fused_graph(rows, idx, alpha):
    w = defaultdict(float)
    for r in rows:
        for t in r.get("edges", []):
            if t in idx and idx[t] != idx[r["id"]]:
                w[tuple(sorted((idx[r["id"]], idx[t])))] += 1.0
    sim = {}
    for r in rows:
        for s in r.get("_similar", []):
            if s["target"] in idx and idx[s["target"]] != idx[r["id"]]:
                e = tuple(sorted((idx[r["id"]], idx[s["target"]])))
                sim[e] = max(sim.get(e, 0.0), float(s["weight"]))
    for e, v in sim.items():
        w[e] += alpha * v
    edges = list(w)
    g = ig.Graph(n=len(rows), edges=edges, directed=False)
    g.es["weight"] = [w[e] for e in edges]
    return g


def node2vec_layout(g, dim=32, walks_per_node=10, walk_len=40, window=5, seed=42):
    n = g.vcount()
    rng = np.random.default_rng(seed)
    nbrs, probs = [], []
    for v in range(n):
        inc = g.incident(v)
        ns = [g.es[e].tuple[0] if g.es[e].tuple[1] == v else g.es[e].tuple[1] for e in inc]
        ws = np.array([g.es[e]["weight"] for e in inc], dtype=float)
        nbrs.append(np.array(ns, dtype=int))
        probs.append(ws / ws.sum() if ws.sum() > 0 else ws)

    co = Counter()
    for _ in range(walks_per_node):
        for start in range(n):
            if len(nbrs[start]) == 0:
                continue
            walk = [start]
            cur = start
            for _ in range(walk_len - 1):
                if len(nbrs[cur]) == 0:
                    break
                cur = int(rng.choice(nbrs[cur], p=probs[cur]))
                walk.append(cur)
            for i, a in enumerate(walk):
                for b in walk[i + 1:i + 1 + window]:
                    if a != b:
                        co[(a, b)] += 1
                        co[(b, a)] += 1

    # PPMI over the walk co-occurrence counts
    rows_i = np.array([k[0] for k in co]); cols_i = np.array([k[1] for k in co])
    vals = np.array([co[k] for k in co], dtype=float)
    total = vals.sum()
    rowsum = np.bincount(rows_i, weights=vals, minlength=n)
    colsum = np.bincount(cols_i, weights=vals, minlength=n)
    pmi = np.log(np.maximum(vals * total / (rowsum[rows_i] * colsum[cols_i]), 1e-12))
    keep = pmi > 0
    from scipy.sparse import csr_matrix
    M = csr_matrix((pmi[keep], (rows_i[keep], cols_i[keep])), shape=(n, n))
    print(f"  [n2v] PPMI matrix nnz={M.nnz} density={M.nnz/(n*n):.3f}")

    emb = TruncatedSVD(n_components=min(dim, n - 1), random_state=seed).fit_transform(M)
    emb = emb / np.maximum(np.linalg.norm(emb, axis=1, keepdims=True), 1e-9)
    import umap
    xy = umap.UMAP(n_neighbors=15, min_dist=0.15, metric="cosine",
                   random_state=seed).fit_transform(emb)
    return np.asarray(xy, dtype=float), emb


def drl_layout(g, seed=42):
    random.seed(seed); np.random.seed(seed)
    lay = g.layout_drl(weights=g.es["weight"], seed=None)
    return np.asarray(lay.coords, dtype=float)


def territory_scores(xy, labels, k=10):
    """Three complementary reads on 'do territories exist on this canvas':
      knn_purity    local — are my 2D neighbours my clustermates?
      silhouette_2d global — are the clusters separated regions?
      centroid_acc  territorial — is each point closest to its OWN cluster's centre?
    `territory` is their mean (silhouette rescaled to [0,1]) and is what selects
    the layout: purity alone rewards locally tidy but globally interleaved maps.
    """
    nn = NearestNeighbors(n_neighbors=min(k + 1, len(xy))).fit(xy)
    _, ind = nn.kneighbors(xy)
    lab = np.asarray(labels)
    purity = float(np.mean([(lab[row[1:]] == lab[i]).mean() for i, row in enumerate(ind)]))
    sil = float(silhouette_score(xy, lab)) if len(set(labels)) > 1 else float("nan")
    ks = sorted(set(labels))
    C = np.array([xy[lab == c].mean(0) for c in ks])
    d = ((xy[:, None, :] - C[None]) ** 2).sum(-1)
    cacc = float((np.array(ks)[d.argmin(1)] == lab).mean())
    return {"knn_purity": purity, "silhouette_2d": sil, "centroid_acc": cacc,
            "territory": float(np.mean([purity, cacc, (sil + 1) / 2]))}


def scatter_trace(fig, rows, members, xy, c, row=None, col=None, showlegend=True):
    meta = NAMES.get(c, {"name": str(c), "nameable": True})
    label = meta["name"] + ("" if meta["nameable"] else "  ⚠")
    tr = go.Scatter(
        x=xy[members, 0], y=xy[members, 1], mode="markers",
        name=f"{label} ({len(members)})", legendgroup=str(c), showlegend=showlegend,
        marker=dict(size=[6 + 2.2 * np.sqrt(rows[i]["centrality"]) for i in members],
                    color=PALETTE[c % len(PALETTE)], opacity=0.78,
                    line=dict(width=0.4, color="rgba(0,0,0,0.35)")),
        text=[f"{rows[i]['title'][:100]}<br>{rows[i]['year']} · "
              f"in-corpus cites {rows[i]['centrality']:.0f}" for i in members],
        hoverinfo="text")
    fig.add_trace(tr, row=row, col=col) if row else fig.add_trace(tr)


def annotate(fig, rows, clusters, xy, row=None, col=None, size=13):
    for c, m in sorted(clusters.items()):
        if len(m) < 5:
            continue
        meta = NAMES.get(c, {"name": str(c), "nameable": True})
        kw = dict(x=float(np.median(xy[m, 0])), y=float(np.median(xy[m, 1])),
                  text=f"<b>{meta['name']}</b>" + ("" if meta["nameable"] else " ⚠"),
                  showarrow=False, font=dict(size=size, color="#111"),
                  bgcolor="rgba(255,255,255,0.82)", borderpad=4)
        fig.add_annotation(row=row, col=col, **kw) if row else fig.add_annotation(**kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alpha", default="0.25")
    ap.add_argument("--source-run", default="l2_th005_clean")
    ap.add_argument("--cluster-run", default="hybrid_a0.25")
    ap.add_argument("--method", default="n2v", choices=["n2v", "drl", "both"])
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--db", default="data/graph_v3_clean")
    ap.add_argument("--freeze", action="store_true", help="write coordinates into the graph")
    args = ap.parse_args()

    sweep = json.loads((EVAL / f"sweep_{args.source_run}.json").read_text())
    mem = sweep["partitions"][args.alpha]["membership"]
    rows = [json.loads(ln) for ln in
            (ROOT / "data" / "processed" / f"interp_{args.source_run}.jsonl").read_text().splitlines()
            if ln.strip()]
    idx = {r["id"]: i for i, r in enumerate(rows)}
    n = len(rows)
    clusters = defaultdict(list)
    for i, c in enumerate(mem):
        clusters[c].append(i)
    g = fused_graph(rows, idx, float(args.alpha))
    print(f"[layout] {n} papers, fused graph {g.ecount()} edges, alpha={args.alpha}")

    old_xy = np.array([[r["layout_x"], r["layout_y"]] for r in rows])
    scores = {"semantic_umap (current)": territory_scores(old_xy, mem)}

    cands = {}
    if args.method in ("n2v", "both"):
        xy, _ = node2vec_layout(g)
        cands["n2v"] = xy
        scores["hybrid_node2vec_umap"] = territory_scores(xy, mem)
    if args.method in ("drl", "both"):
        xy = drl_layout(g)
        cands["drl"] = xy
        scores["hybrid_drl"] = territory_scores(xy, mem)

    print("\n-- do territories read spatially? --")
    print(f"{'layout':<28}{'kNNpur':>9}{'sil2D':>9}{'centroid':>10}{'TERRITORY':>11}")
    for k, v in scores.items():
        print(f"{k:<28}{v['knn_purity']:>9.3f}{v['silhouette_2d']:>9.3f}"
              f"{v['centroid_acc']:>10.3f}{v['territory']:>11.3f}")

    key = {"n2v": "hybrid_node2vec_umap", "drl": "hybrid_drl"}
    best = max(cands, key=lambda k: scores[key[k]]["territory"])
    xy = cands[best]
    run_id = args.run_id or f"{args.cluster_run}_{best}"
    print(f"\n[layout] chosen: {best} → run_id='{run_id}'")

    # ── freeze coordinates ───────────────────────────────────────────────────
    if args.freeze:
        conn = kuzu.Connection(kuzu.Database(str(ROOT / args.db)))
        for i, r in enumerate(rows):
            conn.execute("MATCH (p:Paper {id:$id}) SET p.layout_x=$x, p.layout_y=$y, p.run_id=$run",
                         parameters={"id": r["id"], "x": float(xy[i, 0]),
                                     "y": float(xy[i, 1]), "run": run_id})
        chk = conn.execute("MATCH (p:Paper) RETURN count(p.layout_x), min(p.run_id)").get_next()
        print(f"[layout] frozen into {args.db}: {chk}")

    (EVAL / f"layout_{run_id}.json").write_text(json.dumps({
        "run_id": run_id, "method": best, "alpha": float(args.alpha),
        "cluster_run": args.cluster_run, "scores": scores,
        "coords": {rows[i]["id"]: [float(xy[i, 0]), float(xy[i, 1])] for i in range(n)},
    }, indent=2))

    # ── re-render the same annotated scatter on the new layout ───────────────
    fig = go.Figure()
    for c in sorted(clusters):
        scatter_trace(fig, rows, clusters[c], xy, c)
    annotate(fig, rows, clusters, xy)
    fig.update_layout(
        title=(f"Hybrid clustering on hybrid layout — CITES + {args.alpha}·SIMILAR "
               f"({best}) — {n} papers (⚠ = resists naming)"),
        template="plotly_white", height=860,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        legend=dict(itemsizing="constant", font=dict(size=11)))
    p1 = OUT / f"hybrid_scatter_{run_id}.html"
    fig.write_html(str(p1))

    # ── side by side ─────────────────────────────────────────────────────────
    sb = make_subplots(rows=1, cols=2, horizontal_spacing=0.04, subplot_titles=(
        f"BEFORE — semantic UMAP layout (kNN purity {scores['semantic_umap (current)']['knn_purity']:.2f})",
        f"AFTER — hybrid {best} layout (kNN purity "
        f"{scores[key[best]]['knn_purity']:.2f})"))
    for c in sorted(clusters):
        scatter_trace(sb, rows, clusters[c], old_xy, c, row=1, col=1, showlegend=True)
        scatter_trace(sb, rows, clusters[c], xy, c, row=1, col=2, showlegend=False)
    annotate(sb, rows, clusters, old_xy, row=1, col=1, size=11)
    annotate(sb, rows, clusters, xy, row=1, col=2, size=11)
    sb.update_layout(template="plotly_white", height=760,
                     title="Layout only — same clusters, same names, same colours",
                     legend=dict(itemsizing="constant", font=dict(size=10)))
    sb.update_xaxes(visible=False); sb.update_yaxes(visible=False)
    p2 = OUT / f"layout_sidebyside_{run_id}.html"
    sb.write_html(str(p2))
    print(f"[layout] → {p1}\n[layout] → {p2}")


if __name__ == "__main__":
    main()
