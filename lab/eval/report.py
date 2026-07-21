"""lab/eval/report.py — REPORT-mode metrics + hard-gate inputs for an ingest corpus.

Computes and saves (lab/eval/ingest_report.json):
  • paper count, % with >=1 in-corpus edge, in-corpus edge count
  • year distribution, top venues
  • landmark presence + ranking   (HARD GATE a input)
  • top-N by in-corpus cites       (HARD GATE b input — classify for purity)

Nothing here blocks; the caller enforces the two hard gates.

Usage: python lab/eval/report.py [--corpus data/raw/interp_corpus_v3.jsonl] [--top 50]
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL = Path(__file__).resolve().parent


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(ROOT / "data/raw/interp_corpus_v3.jsonl"))
    ap.add_argument("--top", type=int, default=50)
    args = ap.parse_args()

    rows = [json.loads(ln) for ln in open(args.corpus) if ln.strip()]
    n = len(rows)
    ids = {r["id"] for r in rows}
    for r in rows:
        r["_edges_in"] = [e for e in r.get("edges", []) if e in ids]
    indeg = Counter()
    for r in rows:
        for e in r["_edges_in"]:
            indeg[e] += 1
    for r in rows:
        r["_indeg"] = indeg[r["id"]]
    with_edge = sum(1 for r in rows if r["_indeg"] > 0 or r["_edges_in"])
    years = dict(sorted(Counter(r["year"] for r in rows).items()))
    venues = Counter((r["venue"] or "?") for r in rows).most_common(8)

    # ── landmark presence (HARD GATE a) ──
    lm = json.loads((EVAL / "landmarks.json").read_text())["landmarks"]
    by_ax = {r.get("arxiv_id"): r for r in rows if r.get("arxiv_id")}
    ntitles = {norm(r["title"]): r for r in rows}
    ranking = sorted(rows, key=lambda r: -r["_indeg"])
    rank_of = {r["id"]: i + 1 for i, r in enumerate(ranking)}
    lm_report = []
    for L in lm:
        hit = by_ax.get(L["arxiv_id"])
        if not hit:
            nt = norm(L["title"])
            hit = next((r for k, r in ntitles.items() if nt and (nt in k or k in nt)), None)
        lm_report.append({**L, "tier": L.get("tier", "core"), "present": bool(hit),
                          "in_pool_cites": (hit.get("_in_corpus_cites") if hit else None),
                          "indeg": (hit["_indeg"] if hit else None),
                          "rank": (rank_of.get(hit["id"]) if hit else None)})
    core = [x for x in lm_report if x["tier"] == "core"]
    adj = [x for x in lm_report if x["tier"] != "core"]
    present = sum(1 for x in lm_report if x["present"])
    core_present = sum(1 for x in core if x["present"])
    adj_present = sum(1 for x in adj if x["present"])

    # ── top-N by in-corpus cites (HARD GATE b input) ──
    # NB: rank by `_indeg` (citations from papers INSIDE the final corpus), not by
    # ingest_v3's `_in_corpus_cites`, which counts citations within the whole
    # CANDIDATE POOL. The two diverge badly — generic ML background (GLUE, LLaMA)
    # is heavily cited across the pool but barely inside the corpus, so pool-cites
    # ranking made the purity sample look far more polluted than the corpus is.
    top = sorted(rows, key=lambda r: -r["_indeg"])[:args.top]
    top_out = [{"id": r["id"], "arxiv_id": r.get("arxiv_id"), "year": r["year"],
                "in_pool_cites": r.get("_in_corpus_cites"), "indeg": r["_indeg"],
                "title": r["title"], "abstract": (r.get("abstract") or "")[:320]}
               for r in top]

    report = {
        "corpus": args.corpus, "papers": n,
        "pct_with_edge": round(100 * with_edge / max(n, 1), 1),
        "in_corpus_edges": sum(len(r["_edges_in"]) for r in rows),
        "years": years, "venues": venues,
        "landmarks_present": f"{present}/{len(lm)}",
        "landmarks_core_present": f"{core_present}/{len(core)}",
        "landmarks_adjacent_present": f"{adj_present}/{len(adj)}",
        "gate_a_pass": core_present == len(core),
        "landmarks": lm_report,
        "top_by_in_corpus_cites": top_out,
    }
    (EVAL / "ingest_report.json").write_text(json.dumps(report, indent=2))

    print(f"papers: {n} | %>=1 edge: {report['pct_with_edge']} | in-corpus edges: {report['in_corpus_edges']}")
    print(f"years: {years}")
    print(f"top venues: {venues[:4]}")
    verdict = "PASS" if core_present == len(core) else "FAIL"
    print(f"\nHARD GATE (a) — core landmarks: {core_present}/{len(core)}  → {verdict}")
    for x in core:
        flag = "OK  " if x["present"] else "MISS"
        print(f"  [{flag}] {x['arxiv_id']:>11}  rank={x['rank']}  indeg={x['indeg']}  {x['title'][:46]}")
    print(f"\nadjacent tier (report only): {adj_present}/{len(adj)}")
    for x in adj:
        flag = "ok  " if x["present"] else "--  "
        print(f"  [{flag}] {x['arxiv_id']:>11}  rank={x['rank']}  indeg={x['indeg']}  {x['title'][:46]}")
    print(f"\nTop-{args.top} by in-corpus cites saved → lab/eval/ingest_report.json (classify for purity gate b)")


if __name__ == "__main__":
    main()
