"""lab/eval/l2_report.py — evaluate an L2 run.

Answers three questions with numbers:
  1. Do the centrality baselines rank the known landmarks highly?  (per-metric
     landmark ranking — the metric whose landmark ranks are lowest wins)
  2. Are the clusters real?  (size distribution, tf-idf keywords, top papers)
  3. Do embedding clusters and citation communities agree?  (from l2_stats)

Usage: python lab/eval/l2_report.py --run-id l2_th008
"""
import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL = Path(__file__).resolve().parent

STOP = set("a an the of and or for with to in on by using via is are we our this that "
           "from as at be can do does how what when which why not but their its it".split())


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="l2_th008")
    args = ap.parse_args()

    rows = [json.loads(ln) for ln in
            (ROOT / "data" / "processed" / f"interp_{args.run_id}.jsonl").read_text().splitlines() if ln.strip()]
    stats = json.loads((EVAL / f"l2_stats_{args.run_id}.json").read_text())
    lm = json.loads((EVAL / "landmarks.json").read_text())["landmarks"]
    n = len(rows)

    # ── 1 · landmark ranking per centrality metric ───────────────────────────
    metrics = sorted(rows[0]["_scores"].keys() - {"cite_cluster_id"}) + ["centrality"]
    by_ax = {r.get("arxiv_id"): r for r in rows if r.get("arxiv_id")}
    ntitles = {norm(r["title"]): r for r in rows}

    def find(L):
        hit = by_ax.get(L["arxiv_id"])
        if not hit:
            nt = norm(L["title"])
            hit = next((r for k, r in ntitles.items() if nt and (nt in k or k in nt)), None)
        return hit

    ranks = {}
    for m in metrics:
        key = (lambda r: r["centrality"]) if m == "centrality" else (lambda r: r["_scores"][m])
        order = sorted(rows, key=lambda r: -key(r))
        pos = {r["id"]: i + 1 for i, r in enumerate(order)}
        ranks[m] = pos

    lm_rows, per_metric = [], defaultdict(list)
    for L in lm:
        hit = find(L)
        row = {"arxiv_id": L["arxiv_id"], "title": L["title"], "tier": L.get("tier", "core"),
               "present": bool(hit)}
        if hit:
            for m in metrics:
                row[m] = ranks[m][hit["id"]]
                if L.get("tier", "core") == "core":
                    per_metric[m].append(ranks[m][hit["id"]])
        lm_rows.append(row)

    summary = {}
    for m in metrics:
        rr = per_metric[m]
        if rr:
            summary[m] = {"median_rank": sorted(rr)[len(rr) // 2],
                          "mean_rank": round(sum(rr) / len(rr), 1),
                          "in_top_50": sum(1 for x in rr if x <= 50),
                          "in_top_10pct": sum(1 for x in rr if x <= n * 0.1),
                          "worst_rank": max(rr)}
    best = min(summary, key=lambda m: summary[m]["mean_rank"])

    # ── 2 · cluster profiles ─────────────────────────────────────────────────
    clusters = defaultdict(list)
    for r in rows:
        clusters[r["cluster_id"]].append(r)
    df = Counter()
    for r in rows:
        df.update(set(norm(r["title"]).split()) - STOP)
    profiles = []
    for cid, members in sorted(clusters.items(), key=lambda kv: -len(kv[1])):
        tf = Counter()
        for r in members:
            tf.update(set(norm(r["title"]).split()) - STOP)
        terms = sorted(((t, (c / len(members)) * math.log(n / (1 + df[t])))
                        for t, c in tf.items() if len(t) > 2 and c >= 2),
                       key=lambda x: -x[1])[:8]
        top = sorted(members, key=lambda r: -r["centrality"])[:5]
        profiles.append({
            "cluster_id": cid, "size": len(members),
            "n_subclusters": len({r["subcluster_id"] for r in members}),
            "years_median": sorted(r["year"] for r in members)[len(members) // 2],
            "keywords": [t for t, _ in terms],
            "top_papers": [{"title": r["title"][:80], "year": r["year"],
                            "centrality": round(r["centrality"], 3)} for r in top],
        })

    report = {"run_id": args.run_id, "papers": n, "stats": stats,
              "centrality_summary": summary, "best_metric_by_mean_landmark_rank": best,
              "landmarks": lm_rows, "clusters": profiles}
    out = EVAL / f"l2_report_{args.run_id}.json"
    out.write_text(json.dumps(report, indent=2))

    # ── print ────────────────────────────────────────────────────────────────
    print(f"=== L2 report — {args.run_id} — {n} papers ===")
    print(f"clusters={stats['clusters']} modularity(emb-kNN)={stats['modularity_embedding_knn']:.3f} "
          f"silhouette={stats['silhouette_embedding']:.3f} | "
          f"citation communities={stats['citation_clusters']} "
          f"modularity={stats['modularity_citation']:.3f} | ARI={stats['ari_embedding_vs_citation']:.3f}")
    print(f"SIMILAR edges={stats['similar_edges']}  CITES edges={stats['cite_edges']}")

    print("\n-- centrality baselines vs core landmarks (lower rank = better) --")
    print(f"{'metric':<20}{'median':>8}{'mean':>8}{'top50':>7}{'top10%':>8}{'worst':>7}")
    for m, s in sorted(summary.items(), key=lambda kv: kv[1]["mean_rank"]):
        print(f"{m:<20}{s['median_rank']:>8}{s['mean_rank']:>8}{s['in_top_50']:>7}"
              f"{s['in_top_10pct']:>8}{s['worst_rank']:>7}")
    print(f"→ best by mean landmark rank: {best}")

    print("\n-- landmark ranks under the blended centrality --")
    for r in lm_rows:
        pos = r.get("centrality", "MISS")
        print(f"  [{r['tier']:<8}] rank={str(pos):>5}  {r['title'][:52]}")

    print(f"\n-- clusters ({len(profiles)}) --")
    for p in profiles:
        print(f"  c{p['cluster_id']:<3} n={p['size']:<4} sub={p['n_subclusters']:<3} "
              f"med_year={p['years_median']}  {', '.join(p['keywords'][:6])}")
        print(f"        top: {p['top_papers'][0]['title'][:70]}")
    print(f"\n→ {out}")


if __name__ == "__main__":
    main()
