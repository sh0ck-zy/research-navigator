"""lab/recluster_experiment.py — ISOLATED re-cluster experiments on the v4 corpus.

Decision support for the next freeze, NOT a freeze. Two variants of the fused
hybrid graph (same method as the frozen partition: w = CITES + 0.25*SIMILAR,
Leiden RBConfiguration, resolution 1.0, seeds 1/2/3):

  V1  v4-only      CITES = the deduped v4 corpus `edges` (OpenAlex)
  V2  v4+latex     CITES = union of v4 edges and the latex_refs Stage-3 edges
                   (directed-edge union — an edge both indexes agree on is
                   still ONE edge; the latex index adds, never double-counts)

Node set: the 681 v4 records. The processed l2_th005_clean rows provide the
SIMILAR kNN layer; the two dedupe-absorbed rows are merged into their
canonical twin (max weight per pair). The frozen hybrid partition
(lab/out/viewer_data.json) is the comparison baseline.

Writes ONLY to lab/out/recluster_v4/ — no frozen asset is touched.

Usage:
  python -m lab.recluster_experiment
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

import igraph as ig
import leidenalg
import numpy as np
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed" / "interp_l2_th005_clean.jsonl"
V4 = ROOT / "data" / "raw" / "interp_corpus_v4.jsonl"
RESOLVED = ROOT / "data" / "latex" / "resolved.jsonl"
DEDUPE_MAP = ROOT / "lab" / "eval" / "corpus_dedupe_map.json"
VIEWER = ROOT / "lab" / "out" / "viewer_data.json"
OUT = ROOT / "lab" / "out" / "recluster_v4"

ALPHA = 0.25
RESOLUTION = 1.0
SEEDS = [1, 2, 3]


def load_remap():
    m = json.loads(DEDUPE_MAP.read_text())
    return {w: g["canonical"] for g in m["groups"] for w in g["members"]
            if w != g["canonical"]}


def load_nodes_and_sim(remap):
    """v4 node list + SIMILAR pairs from the processed rows (absorbed rows
    merged into their canonical twin, max weight per pair)."""
    v4 = [json.loads(l) for l in V4.open() if l.strip()]
    wids = [r["id"].split("/")[-1] for r in v4]
    idx = {w: i for i, w in enumerate(wids)}
    sim = {}
    for row in (json.loads(l) for l in PROCESSED.open() if l.strip()):
        u = remap.get(row["id"], row["id"])
        if u not in idx:
            continue
        for s in row.get("_similar") or []:
            v = remap.get(s["target"], s["target"])
            if v in idx and v != u:
                a, b = sorted((idx[u], idx[v]))
                sim[(a, b)] = max(sim.get((a, b), 0.0), float(s["weight"]))
    return v4, wids, idx, sim


def directed_cites_v4(v4, idx):
    """{(src_i, dst_i)} from the v4 corpus edges (already remapped/deduped)."""
    out = set()
    for r in v4:
        u = idx[r["id"].split("/")[-1]]
        for t in r.get("edges") or []:
            if t in idx and idx[t] != u:
                out.add((u, idx[t]))
    return out


def directed_cites_latex(idx, remap):
    """{(src_i, dst_i)} from Stage-3 matched refs, remapped into v4 ids."""
    out = set()
    for r in (json.loads(l) for l in RESOLVED.open() if l.strip()):
        u = remap.get(r["openalex_id"], r["openalex_id"])
        if u not in idx:
            continue
        for m in r["matches"]:
            if m["status"] == "matched":
                v = remap.get(m["corpus_id"], m["corpus_id"])
                if v in idx and v != u:
                    out.add((idx[u], idx[v]))
    return out


def fused_graph(n, directed, sim):
    w = defaultdict(float)
    for u, v in directed:
        w[tuple(sorted((u, v)))] += 1.0     # reciprocal citation -> weight 2, as in the sweep
    for e, s in sim.items():
        w[e] += ALPHA * s
    edges = list(w)
    g = ig.Graph(n=n, edges=edges, directed=False)
    g.es["weight"] = [w[e] for e in edges]
    return g


def run_leiden(g):
    parts = [list(leidenalg.find_partition(
        g, leidenalg.RBConfigurationVertexPartition, weights="weight",
        resolution_parameter=RESOLUTION, seed=s).membership) for s in SEEDS]
    stab = float(np.mean([adjusted_rand_score(parts[i], parts[j])
                          for i in range(len(parts)) for j in range(i + 1, len(parts))]))
    return parts[0], stab                    # seed 1 = representative, as in the sweep


def shape(part):
    sizes = Counter(part)
    n = len(part)
    return {"k": len(sizes),
            "sizes": sorted(sizes.values(), reverse=True),
            "max_cluster_share": max(sizes.values()) / n,
            "singletons": sum(1 for c in sizes.values() if c == 1)}


def frozen_partition(wids, remap):
    """Frozen hybrid cluster per v4 node (absorbed ids folded); None-free."""
    d = json.loads(VIEWER.read_text())
    names = {c["id"]: c["name"] for c in d.get("clusters", [])}
    frozen = {p["id"].split("/")[-1]: p["cluster_id"] for p in d["papers"]}
    for a, c in remap.items():                 # absorbed id -> its twin's cluster
        frozen.setdefault(c, frozen.get(a))
    lab = [frozen.get(w, -1) for w in wids]
    return lab, names


def crosstab(frozen, part, names, top=4):
    """Per frozen cluster: where its papers land in the new partition."""
    per = defaultdict(Counter)
    for f, p in zip(frozen, part):
        per[f][p] += 1
    out = {}
    for f, c in sorted(per.items()):
        total = sum(c.values())
        out[f"{f} {names.get(f, '?')}"] = {
            "n": total,
            "lands_in": [{"new_cluster": k, "n": v} for k, v in c.most_common(top)],
            "intact_share": round(c.most_common(1)[0][1] / total, 3)}
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    remap = load_remap()
    v4, wids, idx, sim = load_nodes_and_sim(remap)
    n = len(wids)
    oa = directed_cites_v4(v4, idx)
    lx = directed_cites_latex(idx, remap)
    union = oa | lx
    print(f"nodes {n}; directed edges: OA {len(oa)}, latex {len(lx)}, "
          f"union {len(union)} (latex adds {len(union) - len(oa)})")

    frozen, names = frozen_partition(wids, remap)
    report = {"nodes": n, "alpha": ALPHA, "resolution": RESOLUTION, "seeds": SEEDS,
              "edges": {"oa_directed": len(oa), "latex_directed": len(lx),
                        "union_directed": len(union),
                        "latex_novel": len(union) - len(oa)},
              "variants": {}}
    parts = {}
    for tag, directed in (("v1_v4_only", oa), ("v2_v4_plus_latex", union)):
        g = fused_graph(n, directed, sim)
        part, stab = run_leiden(g)
        parts[tag] = part
        report["variants"][tag] = {
            **shape(part), "stability": round(stab, 4),
            "graph_edges": g.ecount(),
            "ari_vs_frozen": round(adjusted_rand_score(frozen, part), 4),
            "nmi_vs_frozen": round(normalized_mutual_info_score(frozen, part), 4),
            "frozen_crosstab": crosstab(frozen, part, names)}
        s = report["variants"][tag]
        print(f"{tag}: k={s['k']} sizes={s['sizes'][:8]} stab={s['stability']} "
              f"ARIvsFrozen={s['ari_vs_frozen']}")

    report["v1_vs_v2"] = {
        "ari": round(adjusted_rand_score(parts["v1_v4_only"], parts["v2_v4_plus_latex"]), 4),
        "nmi": round(normalized_mutual_info_score(parts["v1_v4_only"], parts["v2_v4_plus_latex"]), 4)}
    print(f"V1 vs V2: ARI={report['v1_vs_v2']['ari']} NMI={report['v1_vs_v2']['nmi']}")

    (OUT / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    (OUT / "partitions.json").write_text(json.dumps(
        {"wids": wids, **{k: v for k, v in parts.items()}}, ensure_ascii=False))
    print(f"wrote {OUT}/report.json + partitions.json")


if __name__ == "__main__":
    main()
