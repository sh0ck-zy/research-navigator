"""lab/freeze_v2latex.py — freeze the VALIDATED V2 partition (v4 + latex edges).

Succeeds hybrid_a0.25 as the canonical clustering, per decision of 2026-07-24.
Validation that preceded this freeze (see lab/out/recluster_v4/validation.json):
all sweep feasible() bars pass; landmark ARI 0.678 vs the frozen baseline's
0.507; stability 0.669 vs 0.643; human naming pass: 6/8 nameable (frozen: 5/8).

What it does (mirrors lab/freeze_clustering.py):
  - rebuilds the V2 fused graph (CITES = v4 ∪ latex directed edges, + 0.25*SIM)
    via lab.recluster_experiment, derives level-2 subclusters (res 1.5, seed 1)
  - writes cluster_id / subcluster_id / run_id into data/graph_v3_clean;
    the two dedupe-absorbed twins receive their canonical's assignment
  - writes lab/eval/cluster_names_hybrid_v4latex_a0.25.json (names authored by
    reading ~28 sampled papers per cluster; resists-naming recorded honestly)
  - renders lab/out/hybrid_scatter_hybrid_v4latex_a0.25.html on the UNCHANGED
    stored layout (re-layout is a separate, later decision)

The pre-freeze state is preserved in
lab/out/recluster_v4/frozen_backup_hybrid_a0.25.json for rollback.

Usage:
  python -m lab.freeze_v2latex
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

import igraph as ig
import kuzu
import leidenalg
import numpy as np
import plotly.graph_objects as go

from lab.recluster_experiment import (fused_graph, load_nodes_and_sim, load_remap,
                                      directed_cites_latex, directed_cites_v4)
from lab.sweep_hybrid import STOP, norm, tfidf_names

ROOT = Path(__file__).resolve().parent.parent
EVAL = ROOT / "lab" / "eval"
OUT = ROOT / "lab" / "out"
PARTS = OUT / "recluster_v4" / "partitions.json"
DB = ROOT / "data" / "graph_v3_clean"
RUN_ID = "hybrid_v4latex_a0.25_drl"   # _drl: layout coords unchanged from the DRL run
SUB_RESOLUTION = 1.5

# Authored 2026-07-24 by reading ~28 sampled papers per cluster (top-centrality
# + random), per the original freeze protocol. `nameable: false` = only a
# conjunction or grab-bag label fits — recorded as a failure, not dressed up.
NAMES = {
    0: {"name": "Attribution & Classic XAI", "nameable": True},
    1: {"name": "Factual Knowledge & Editing", "nameable": True},
    2: {"name": "BERT-Era Probing", "nameable": True},
    3: {"name": "Foundation Models & LLM Substrate", "nameable": True,
        "why": "core is crisp (LLaMA/ViT/FlashAttention — the cited substrate, "
               "not interp itself) but the applications tail is heterogeneous."},
    4: {"name": "Linear Representations & Steering", "nameable": True},
    5: {"name": "Circuits, Grokking & ICL", "nameable": True,
        "why": "one minority strand (psycholinguistic surprisal/reading-time "
               "work, ~15%) rides along via the cognitive-modeling papers."},
    6: {"name": "Sparse Autoencoders / Bio-LMs", "nameable": False,
        "why": "still the two-theme fusion of the old cluster 5 (SAE/dictionary "
               "learning + protein/DNA LMs). The SAE-on-protein-LM crossover "
               "papers are a real bridge now, but the bio/clinical tail is a "
               "grab-bag; only a conjunction names the whole."},
    7: {"name": "(singleton)", "nameable": False, "why": "one paper, infant psychology."},
}


def main():
    parts = json.loads(PARTS.read_text())
    wids, mem = parts["wids"], parts["v2_v4_plus_latex"]
    remap = load_remap()
    v4, wids2, idx, sim = load_nodes_and_sim(remap)
    assert wids2 == wids, "partition frame and v4 frame diverged"
    n = len(wids)

    # V2 fused graph -> level-2 subclusters, same recipe as the original freeze
    directed = directed_cites_v4(v4, idx) | directed_cites_latex(idx, remap)
    g = fused_graph(n, directed, sim)
    sub = [0] * n
    clusters = defaultdict(list)
    for i, c in enumerate(mem):
        clusters[c].append(i)
    for c, members in clusters.items():
        if len(members) < 8:
            continue
        sg = g.subgraph(members)
        p = leidenalg.find_partition(sg, leidenalg.RBConfigurationVertexPartition,
                                     weights="weight", resolution_parameter=SUB_RESOLUTION,
                                     seed=1)
        for local, m in enumerate(members):
            sub[m] = p.membership[local]

    # processed rows give layout/centrality/titles for scatter + exemplars
    rows_all = {r["id"]: r for r in
                (json.loads(l) for l in
                 (ROOT / "data" / "processed" / "interp_l2_th005_clean.jsonl").open()
                 if l.strip())}
    rows = [rows_all[w] for w in wids]
    titles = [r["title"] for r in rows]

    # ── write back into Kùzu (absorbed twins get their canonical's assignment) ─
    conn = kuzu.Connection(kuzu.Database(str(DB)))
    pos = {w: i for i, w in enumerate(wids)}
    n_wrote = 0
    for wid_db in list(pos) + list(remap):
        i = pos[remap.get(wid_db, wid_db)] if wid_db in remap else pos[wid_db]
        conn.execute(
            "MATCH (p:Paper {id:$id}) SET p.cluster_id=$c, p.subcluster_id=$s, p.run_id=$run",
            parameters={"id": wid_db, "c": int(mem[i]), "s": int(sub[i]), "run": RUN_ID})
        n_wrote += 1
    chk = conn.execute("MATCH (p:Paper) RETURN count(*), count(p.cluster_id), min(p.run_id), max(p.run_id)").get_next()
    print(f"[freeze] wrote {n_wrote} assignments; graph check: {chk}")

    # ── names artifact ───────────────────────────────────────────────────────
    df = Counter()
    for t in titles:
        df.update(set(norm(t).split()) - STOP)
    # tfidf_names takes ONE cluster's member indices -> (terms, hit_share)
    top_terms = {c: tfidf_names(members, titles, df, n)[0]
                 for c, members in clusters.items()}
    names_out = {"run_id": RUN_ID, "alpha": 0.25, "source": "lab/out/recluster_v4 (V2)",
                 "cites": "v4 OpenAlex ∪ latex_refs Stage-3 (directed union)",
                 "predecessor": "hybrid_a0.25_drl (backup: lab/out/recluster_v4/"
                                "frozen_backup_hybrid_a0.25.json)",
                 "clusters": []}
    for c in sorted(clusters):
        meta = NAMES.get(c, {"name": f"cluster {c}", "nameable": False})
        top = sorted(clusters[c], key=lambda i: -rows[i]["centrality"])[:5]
        names_out["clusters"].append({
            "cluster_id": c, "name": meta["name"], "nameable": meta["nameable"],
            "why_not": meta.get("why"), "size": len(clusters[c]),
            "n_subclusters": len({sub[i] for i in clusters[c]}),
            "top_terms": top_terms.get(c, []),
            "exemplars": [rows[i]["title"][:90] for i in top]})
    out_names = EVAL / f"cluster_names_{RUN_ID}.json"
    out_names.write_text(json.dumps(names_out, indent=2, ensure_ascii=False))
    print(f"[freeze] names → {out_names}")

    # ── annotated scatter on the unchanged layout ────────────────────────────
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
        title=(f"Hybrid clustering v4+latex — CITES∪LaTeX + 0.25·SIMILAR — {n} papers, "
               f"{len(clusters)} clusters (⚠ = resists naming)"),
        template="plotly_white", height=860,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        legend=dict(itemsizing="constant", font=dict(size=11)))
    out_html = OUT / f"hybrid_scatter_{RUN_ID}.html"
    fig.write_html(str(out_html))
    print(f"[freeze] annotated scatter → {out_html}")


if __name__ == "__main__":
    main()
