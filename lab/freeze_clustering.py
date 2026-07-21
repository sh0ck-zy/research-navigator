"""lab/freeze_clustering.py — freeze the winning hybrid partition as canonical.

Writes cluster_id / subcluster_id / run_id back into the Kùzu graph (schema
unchanged), saves the cluster names, and renders the annotated scatter.

Level-2 subclusters are recomputed on the same fused graph so cluster_id and
subcluster_id describe the same partitioning, not two different runs.

Usage:
  python lab/freeze_clustering.py --alpha 0.25 --run-id hybrid_a0.25
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

import igraph as ig
import kuzu
import leidenalg
import numpy as np
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parent.parent
EVAL = ROOT / "lab" / "eval"
OUT = ROOT / "lab" / "out"

# 2-4 word names, written by reading ~30 sampled papers per cluster (highest
# centrality + a random sample). `nameable: false` marks a cluster that only
# admits a conjunction or a grab-bag label — criterion 2 says that is a bad
# cluster, and these are recorded as failures rather than dressed up.
NAMES = {
    0: {"name": "Factual Knowledge & Editing", "nameable": True},
    1: {"name": "Attribution & Feature Visualization", "nameable": True},
    2: {"name": "Latent Representations & Safety", "nameable": True},
    3: {"name": "BERT-Era Probing", "nameable": True},
    4: {"name": "Circuits & Superposition", "nameable": True},
    5: {"name": "Sparse Autoencoders / Bio-LMs", "nameable": False,
        "why": "two unrelated themes fused: SAE/dictionary-learning work and protein/DNA "
               "language models. Only a conjunction names it."},
    6: {"name": "Multimodal & Architecture Misc", "nameable": False,
        "why": "grab-bag: ViT, wav2vec, speech, pose estimation, layer-norm analysis. "
               "No shared subject beyond 'transformer-adjacent'."},
    7: {"name": "(singleton)", "nameable": False, "why": "one paper, infant psychology."},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alpha", default="0.25")
    ap.add_argument("--source-run", default="l2_th005_clean")
    ap.add_argument("--run-id", default="hybrid_a0.25")
    ap.add_argument("--db", default="data/graph_v3_clean")
    ap.add_argument("--sub-resolution", type=float, default=1.5)
    args = ap.parse_args()

    sweep = json.loads((EVAL / f"sweep_{args.source_run}.json").read_text())
    mem = sweep["partitions"][args.alpha]["membership"]
    rows = [json.loads(ln) for ln in
            (ROOT / "data" / "processed" / f"interp_{args.source_run}.jsonl").read_text().splitlines()
            if ln.strip()]
    n = len(rows)
    idx = {r["id"]: i for i, r in enumerate(rows)}
    alpha = float(args.alpha)

    # rebuild the fused graph to derive level-2 subclusters
    # same fusion as sweep_hybrid: citation pairs count, similarity pairs are
    # deduped by max (a->b and b->a both appear in _similar) then scaled by alpha
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
    g = ig.Graph(n=n, edges=edges, directed=False)
    g.es["weight"] = [w[e] for e in edges]

    sub = [0] * n
    clusters = defaultdict(list)
    for i, c in enumerate(mem):
        clusters[c].append(i)
    for c, members in clusters.items():
        if len(members) < 8:
            continue
        sg = g.subgraph(members)
        p = leidenalg.find_partition(sg, leidenalg.RBConfigurationVertexPartition,
                                     weights="weight", resolution_parameter=args.sub_resolution,
                                     seed=1)
        for local, m in enumerate(members):
            sub[m] = p.membership[local]

    # ── write back into Kùzu ─────────────────────────────────────────────────
    conn = kuzu.Connection(kuzu.Database(str(ROOT / args.db)))
    for i, r in enumerate(rows):
        conn.execute(
            "MATCH (p:Paper {id:$id}) SET p.cluster_id=$c, p.subcluster_id=$s, p.run_id=$run",
            parameters={"id": r["id"], "c": int(mem[i]), "s": int(sub[i]), "run": args.run_id})
    chk = conn.execute("MATCH (p:Paper) RETURN count(*), count(p.cluster_id), min(p.run_id)").get_next()
    print(f"[freeze] wrote cluster_id/subcluster_id/run_id → {chk} in {args.db}")

    # ── names artifact ───────────────────────────────────────────────────────
    detail = sweep["partitions"][args.alpha]["detail"]
    names_out = {"run_id": args.run_id, "alpha": alpha, "source_run": args.source_run,
                 "clusters": []}
    for c in sorted(clusters):
        meta = NAMES.get(c, {"name": f"cluster {c}", "nameable": False})
        top = sorted(clusters[c], key=lambda i: -rows[i]["centrality"])[:5]
        names_out["clusters"].append({
            "cluster_id": c, "name": meta["name"], "nameable": meta["nameable"],
            "why_not": meta.get("why"), "size": len(clusters[c]),
            "n_subclusters": len({sub[i] for i in clusters[c]}),
            "top_terms": detail["top_terms"].get(str(c), []),
            "exemplars": [rows[i]["title"][:90] for i in top],
        })
    (EVAL / f"cluster_names_{args.run_id}.json").write_text(json.dumps(names_out, indent=2))

    # ── annotated scatter ────────────────────────────────────────────────────
    # Positions are the existing UMAP-of-embeddings layout stored in the graph, so
    # this also shows honestly how the hybrid partition sits against semantic space.
    palette = ["#4C9BE8", "#E8734C", "#5FC27E", "#C878E0", "#E8C64C",
               "#4CD3E8", "#E85C8A", "#9AA6B2", "#8A7CE0"]
    fig = go.Figure()
    for c in sorted(clusters):
        m = clusters[c]
        meta = NAMES.get(c, {"name": str(c), "nameable": True})
        label = meta["name"] + ("" if meta["nameable"] else "  ⚠")
        fig.add_trace(go.Scatter(
            x=[rows[i]["layout_x"] for i in m], y=[rows[i]["layout_y"] for i in m],
            mode="markers", name=f"{label} ({len(m)})",
            marker=dict(size=[6 + 2.2 * np.sqrt(rows[i]["centrality"]) for i in m],
                        color=palette[c % len(palette)], opacity=0.78,
                        line=dict(width=0.4, color="rgba(0,0,0,0.35)")),
            text=[f"{rows[i]['title'][:100]}<br>{rows[i]['year']} · "
                  f"in-corpus cites {rows[i]['centrality']:.0f}" for i in m],
            hoverinfo="text"))
    for c in sorted(clusters):
        m = clusters[c]
        if len(m) < 5:
            continue
        meta = NAMES.get(c, {"name": str(c), "nameable": True})
        fig.add_annotation(
            x=float(np.median([rows[i]["layout_x"] for i in m])),
            y=float(np.median([rows[i]["layout_y"] for i in m])),
            text=f"<b>{meta['name']}</b>" + ("" if meta["nameable"] else " ⚠"),
            showarrow=False, font=dict(size=13, color="#111"),
            bgcolor="rgba(255,255,255,0.82)", borderpad=4)
    fig.update_layout(
        title=(f"Hybrid clustering — CITES + {alpha}·SIMILAR — {n} papers, "
               f"{len(clusters)} clusters (⚠ = resists naming)"),
        template="plotly_white", height=860,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        legend=dict(itemsizing="constant", font=dict(size=11)))
    out = OUT / f"hybrid_scatter_{args.run_id}.html"
    fig.write_html(str(out))
    print(f"[freeze] annotated scatter → {out}")


if __name__ == "__main__":
    main()
