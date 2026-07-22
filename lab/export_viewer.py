"""lab/export_viewer.py — export viewer_data.json for the lab map viewer.

Single data file, single source of truth: the frozen Kùzu graph
(data/graph_v3_clean, run_id='hybrid_a0.25_drl'). The viewer hardcodes
NOTHING about clusters, names, counts or positions — after a re-cluster,
re-run this exporter and the viewer follows.

Emits lab/out/viewer_data.json:
  meta      {run_id, n_papers, n_edges, generated_from}
  clusters  [{id, name, nameable, one_liner, paper_count, centroid, color}]
  flows     top ~10 inter-cluster CITES aggregates [{a, b, count}]
  papers    [{id, title, authors, year, venue, x, y, cluster_id, centrality,
              membership, membership_2nd}]
  edges     {paper_id: [cited_paper_ids]}   (in-corpus CITES only, directed)

membership       label-propagation self-cluster mass over the fused graph
                 (same fusion + same alpha/iters family as ingest_v3's
                 label_propagation), min-max normalized per cluster.
membership_2nd   nearest OTHER cluster by aggregate SIMILAR weight.

Usage:
  python lab/export_viewer.py
"""
import json
from collections import defaultdict
from pathlib import Path

import kuzu
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
EVAL = ROOT / "lab" / "eval"
OUT = ROOT / "lab" / "out"

DB = "data/graph_v3_clean"
NAMES_FILE = EVAL / "cluster_names_hybrid_a0.25.json"
FUSION_ALPHA = 0.25   # same fusion the frozen clustering used
LP_ALPHA, LP_ITERS = 0.55, 6  # same params as ingest_v3.label_propagation
TOP_FLOWS = 10

# One-liners are DATA (they ride in viewer_data.json, never in the viewer).
# Keyed by cluster_id, guarded by the names artifact's run_id below; unknown
# clusters fall back to their top terms.
ONE_LINERS = {
    "hybrid_a0.25": {
        0: "Where facts live in transformers — locating and rewriting a model's stored knowledge.",
        1: "The classic explainability toolkit: saliency, attribution, and visualizing what deep nets see.",
        2: "What models represent internally — world models, truth directions, steering and safety.",
        3: "Probing classifiers and attention analysis from the BERT era of NLP interpretability.",
        4: "Reverse-engineering computation: circuits, induction heads, superposition, grokking.",
        5: "An uneasy pair: sparse-autoencoder dictionary learning fused with protein/DNA language models.",
        6: "A grab-bag at the edges: vision, speech and architecture analysis adjacent to interp.",
        7: "A lone outlier: an infant-psychology replication with no ties to the field.",
    },
}


def main():
    conn = kuzu.Connection(kuzu.Database(str(ROOT / DB), read_only=True))

    res = conn.execute(
        "MATCH (p:Paper) RETURN p.id, p.title, p.authors, p.year, p.venue, "
        "p.cluster_id, p.layout_x, p.layout_y, p.centrality, p.run_id")
    papers, run_ids = [], set()
    while res.has_next():
        pid, title, authors, year, venue, cid, x, y, cent, run = res.get_next()
        papers.append(dict(id=pid, title=title, authors=authors or [], year=year,
                           venue=venue, cluster_id=int(cid), x=float(x), y=float(y),
                           centrality=float(cent)))
        run_ids.add(run)
    assert run_ids == {"hybrid_a0.25_drl"}, f"unexpected run_ids in graph: {run_ids}"
    idx = {p["id"]: i for i, p in enumerate(papers)}
    n = len(papers)
    print(f"[export] {n} papers, run_id={run_ids}")

    res = conn.execute("MATCH (a:Paper)-[:CITES]->(b:Paper) RETURN a.id, b.id")
    cites = []
    while res.has_next():
        a, b = res.get_next()
        cites.append((a, b))
    res = conn.execute("MATCH (a:Paper)-[s:SIMILAR]->(b:Paper) RETURN a.id, b.id, s.weight")
    similar = []
    while res.has_next():
        a, b, w = res.get_next()
        similar.append((a, b, float(w)))
    print(f"[export] {len(cites)} CITES, {len(similar)} SIMILAR")

    # ── fused graph (identical fusion to freeze_clustering / layout_hybrid) ──
    w = defaultdict(float)
    for a, b in cites:
        if idx[a] != idx[b]:
            w[tuple(sorted((idx[a], idx[b])))] += 1.0
    sim_pair = {}
    for a, b, sw in similar:
        if idx[a] != idx[b]:
            e = tuple(sorted((idx[a], idx[b])))
            sim_pair[e] = max(sim_pair.get(e, 0.0), sw)
    for e, v in sim_pair.items():
        w[e] += FUSION_ALPHA * v
    nbrs = defaultdict(list)
    for (i, j), v in w.items():
        nbrs[i].append((j, v))
        nbrs[j].append((i, v))

    # ── membership strength: label propagation of one-hot cluster labels ─────
    labels = np.array([p["cluster_id"] for p in papers])
    ks = sorted(set(labels.tolist()))
    kpos = {c: i for i, c in enumerate(ks)}
    onehot = np.zeros((n, len(ks)))
    onehot[np.arange(n), [kpos[c] for c in labels]] = 1.0
    dist = onehot.copy()
    for _ in range(LP_ITERS):
        nxt = np.array(dist)
        for i in range(n):
            if not nbrs[i]:
                continue
            tot = sum(v for _, v in nbrs[i])
            neigh = np.zeros(len(ks))
            for j, v in nbrs[i]:
                neigh += v * dist[j]
            nxt[i] = LP_ALPHA * onehot[i] + (1 - LP_ALPHA) * neigh / tot
        dist = nxt
    raw = dist[np.arange(n), [kpos[c] for c in labels]]

    membership = np.zeros(n)
    for c in ks:
        m = labels == c
        lo, hi = raw[m].min(), raw[m].max()
        membership[m] = 1.0 if hi - lo < 1e-9 else (raw[m] - lo) / (hi - lo)

    # ── membership_2nd: nearest OTHER cluster by aggregate SIMILAR weight ────
    sim_mass = defaultdict(lambda: defaultdict(float))
    for a, b, sw in similar:
        ia, ib = idx[a], idx[b]
        sim_mass[ia][labels[ib]] += sw
        sim_mass[ib][labels[ia]] += sw
    second = []
    for i in range(n):
        cands = {c: v for c, v in sim_mass[i].items() if c != labels[i]}
        if cands:
            second.append(int(max(cands, key=cands.get)))
        else:  # fallback: second-best label-prop cluster, else none
            order = np.argsort(-dist[i])
            alt = [ks[k] for k in order if ks[k] != labels[i] and dist[i][k] > 0]
            second.append(int(alt[0]) if alt else None)

    # ── inter-cluster flow matrix (in-corpus CITES aggregated per pair) ──────
    flow = defaultdict(int)
    for a, b in cites:
        ca, cb = int(labels[idx[a]]), int(labels[idx[b]])
        if ca != cb:
            flow[tuple(sorted((ca, cb)))] += 1
    flows = [{"a": a, "b": b, "count": c}
             for (a, b), c in sorted(flow.items(), key=lambda kv: -kv[1])[:TOP_FLOWS]]
    print(f"[export] flows kept: {flows}")

    # ── clusters ─────────────────────────────────────────────────────────────
    names_doc = json.loads(NAMES_FILE.read_text())
    liners = ONE_LINERS.get(names_doc["run_id"], {})
    by_id = {c["cluster_id"]: c for c in names_doc["clusters"]}
    palette = ["#4C9BE8", "#E8734C", "#5FC27E", "#C878E0", "#E8C64C",
               "#4CD3E8", "#E85C8A", "#9AA6B2", "#8A7CE0"]
    clusters = []
    for c in ks:
        m = labels == c
        xs = np.array([p["x"] for p in papers])[m]
        ys = np.array([p["y"] for p in papers])[m]
        meta = by_id.get(c, {})
        clusters.append({
            "id": int(c),
            "name": meta.get("name", f"cluster {c}"),
            "nameable": meta.get("nameable", True),
            "one_liner": liners.get(c, ", ".join(meta.get("top_terms", [])) or "—"),
            "paper_count": int(m.sum()),
            "centroid": [float(np.median(xs)), float(np.median(ys))],
            "color": palette[c % len(palette)],
        })

    edges_adj = defaultdict(list)
    for a, b in cites:
        edges_adj[a].append(b)

    out = {
        "meta": {"run_id": "hybrid_a0.25_drl", "cluster_run": names_doc["run_id"],
                 "n_papers": n, "n_edges": len(cites),
                 "generated_from": DB},
        "clusters": clusters,
        "flows": flows,
        "papers": [{
            "id": p["id"], "title": p["title"], "authors": p["authors"],
            "year": p["year"], "venue": p["venue"],
            "x": round(p["x"], 3), "y": round(p["y"], 3),
            "cluster_id": p["cluster_id"], "centrality": p["centrality"],
            "membership": round(float(membership[i]), 4),
            "membership_2nd": second[i],
        } for i, p in enumerate(papers)],
        "edges": dict(edges_adj),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "viewer_data.json"
    path.write_text(json.dumps(out))
    kb = path.stat().st_size / 1024
    print(f"[export] → {path} ({kb:.0f} KB)")

    # sanity: landmark visibility (acceptance test 2)
    toy = [p for p in papers if "Toy Models of Superposition" in p["title"]]
    for t in toy:
        peers = sorted([p for p in papers if p["cluster_id"] == t["cluster_id"]],
                       key=lambda p: -p["centrality"])
        rank = [p["id"] for p in peers].index(t["id"]) + 1
        print(f"[sanity] '{t['title']}' cluster={t['cluster_id']} "
              f"centrality={t['centrality']:.0f} rank_in_cluster={rank}")


if __name__ == "__main__":
    main()
