"""lab/latex_refs/resolve_ids.py — Stage 0: resolve each corpus paper to an arXiv id.

Only 182/683 corpus records carry a local arXiv id (field or arxiv-DOI). The
rest are OpenAlex records with no stored arXiv linkage. To fetch e-print source
we need the id, so this stage does ONE paced arXiv api/query title search per
locally-unresolved paper and accepts the top hit ONLY if it passes a strict
programmatic gate — we never force a match.

Gate (all three required, per the workstream contract):
  - title_sim   >= 0.92   (rapidfuzz token_set_ratio, normalized)
  - author_overlap >= 1   (surname intersection with the OpenAlex record)
  - |year_diff| <= 2

Statuses:
  local        arXiv id from a local field          -> resolved universe
  searched     arXiv id from search, gate passed     -> resolved universe
  unresolved   candidates found, none passed the gate (raw kept for spot-check)
  no_arxiv_id  search returned nothing (journal/bioRxiv-only — expected)
  search_error arXiv api/query failed after retries (retryable: delete the ckpt)

OpenAlex and S2 are NOT called here and remain forbidden. The only egress is
arXiv api/query, one request per paper, paced >=3s.

Usage:
  python -m lab.latex_refs.resolve_ids                 # full run (resumable)
  python -m lab.latex_refs.resolve_ids --limit 20      # smoke test
  python -m lab.latex_refs.resolve_ids --no-search     # local pass only
"""
import argparse
import sys
import time
import xml.etree.ElementTree as ET
from urllib.parse import quote
from urllib.request import Request, urlopen

from .common import (EVAL, LATEX, aggregate, load_corpus, load_ckpt, local_arxiv_id,
                     norm, oa_key, pct, print_status_by_cluster, save_ckpt, surnames,
                     title_sim)

STAGE = "ids"
ARXIV_API = "http://export.arxiv.org/api/query"
UA = "clarity-research/latex_refs (mailto:sh0ck.zy.25@gmail.com)"
ATOM = "{http://www.w3.org/2005/Atom}"
PACE = 3.0            # seconds between arXiv requests
TITLE_MIN = 0.92
YEAR_MAX = 2


def arxiv_search(title, retries=3):
    """One arXiv api/query title search. Returns list of candidate dicts
    (arxiv_id, title, authors, year). Raises on hard failure after retries."""
    q = norm(title)
    if not q:
        return []
    url = f'{ARXIV_API}?search_query=ti:%22{quote(q)}%22&start=0&max_results=10'
    last = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": UA})
            with urlopen(req, timeout=60) as r:
                raw = r.read()
            root = ET.fromstring(raw)
            out = []
            for e in root.findall(f"{ATOM}entry"):
                idtxt = (e.findtext(f"{ATOM}id") or "").strip()
                axid = idtxt.rsplit("/abs/", 1)[-1] if "/abs/" in idtxt else ""
                axid = axid.split("v")[0] if axid[:4].isdigit() else axid
                pub = (e.findtext(f"{ATOM}published") or "")[:4]
                out.append({
                    "arxiv_id": axid,
                    "title": (e.findtext(f"{ATOM}title") or "").strip(),
                    "authors": [n.text for n in e.findall(f"{ATOM}author/{ATOM}name")],
                    "year": int(pub) if pub.isdigit() else None,
                })
            return out
        except Exception as ex:  # noqa: BLE001 — transient network/XML; retry then give up
            last = ex
            time.sleep(PACE * (attempt + 1))
    raise last


def verify(rec, cand):
    """Score a candidate against the OpenAlex record. Returns (scores, passed)."""
    ts = title_sim(rec.get("title"), cand.get("title"))
    ov = len(surnames(rec.get("authors")) & surnames(cand.get("authors")))
    ry, cy = rec.get("year"), cand.get("year")
    yd = abs(ry - cy) if (ry and cy) else None
    passed = (ts >= TITLE_MIN and ov >= 1 and yd is not None and yd <= YEAR_MAX)
    return {"title_sim": round(ts, 4), "author_overlap": ov, "year_diff": yd}, passed


def process(rec, do_search):
    wid = oa_key(rec)
    base = {"openalex_id": wid, "title": rec.get("title"), "year": rec.get("year")}

    ax = local_arxiv_id(rec)
    if ax:
        return {**base, "status": "local", "method": "field", "arxiv_id": ax,
                "verify": None, "candidate": None, "n_candidates": None}

    if not do_search:
        return {**base, "status": "unresolved", "method": None, "arxiv_id": None,
                "verify": None, "candidate": None, "n_candidates": None, "_deferred": True}

    time.sleep(PACE)
    try:
        cands = arxiv_search(rec.get("title"))
    except Exception as ex:  # noqa: BLE001
        return {**base, "status": "search_error", "method": "search", "arxiv_id": None,
                "verify": None, "candidate": None, "n_candidates": None, "error": str(ex)[:200]}

    if not cands:
        return {**base, "status": "no_arxiv_id", "method": "search", "arxiv_id": None,
                "verify": None, "candidate": None, "n_candidates": 0}

    scored = sorted(((verify(rec, c), c) for c in cands),
                    key=lambda x: x[0][0]["title_sim"], reverse=True)
    (best_scores, passed), best = scored[0]
    cand_view = {k: best.get(k) for k in ("arxiv_id", "title", "authors", "year")}
    if passed:
        return {**base, "status": "searched", "method": "search", "arxiv_id": best["arxiv_id"],
                "verify": best_scores, "candidate": cand_view, "n_candidates": len(cands)}
    return {**base, "status": "unresolved", "method": "search", "arxiv_id": None,
            "verify": best_scores, "candidate": cand_view, "n_candidates": len(cands)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="process at most N papers")
    ap.add_argument("--no-search", action="store_true", help="local pass only, no arXiv calls")
    ap.add_argument("--force", action="store_true", help="ignore existing checkpoints")
    args = ap.parse_args()

    corpus = load_corpus()
    if args.limit:
        corpus = corpus[: args.limit]

    total = len(corpus)
    done = 0
    for i, rec in enumerate(corpus, 1):
        wid = oa_key(rec)
        if not args.force:
            cached = load_ckpt(STAGE, wid)
            # A deferred no-search placeholder is not a real result — reprocess it
            # when search is enabled.
            if cached and not (cached.get("_deferred") and not args.no_search):
                done += 1
                continue
        res = process(rec, do_search=not args.no_search)
        save_ckpt(STAGE, wid, res)
        done += 1
        tag = res["status"]
        extra = f" -> {res['arxiv_id']}" if res.get("arxiv_id") else ""
        if res.get("verify"):
            extra += f"  ts={res['verify']['title_sim']} ov={res['verify']['author_overlap']} yd={res['verify']['year_diff']}"
        print(f"[{i}/{total}] {wid} {tag}{extra}", flush=True)

    write_reports()
    print(f"\nStage 0 complete: {done}/{total} papers checkpointed.")


def write_reports():
    """Aggregate ckpts -> data/latex/ids.jsonl and lab/eval/arxiv_id_resolution.json."""
    recs = aggregate(STAGE, "ids.jsonl")
    from collections import Counter
    counts = Counter(r["status"] for r in recs)
    resolved = counts["local"] + counts["searched"]
    n = len(recs)

    # Spot-check log: EVERY searched/unresolved decision with its scores.
    import json
    audit = [{
        "openalex_id": r["openalex_id"], "title": r["title"], "year": r.get("year"),
        "status": r["status"], "arxiv_id": r.get("arxiv_id"),
        "verify": r.get("verify"), "candidate": r.get("candidate"),
    } for r in recs if r["status"] in ("searched", "unresolved", "search_error")]
    report = {
        "denominator_note": "coverage measured over all 683 corpus papers",
        "total": n,
        "status_counts": dict(counts),
        "resolved_universe": resolved,
        "coverage": pct(resolved, n),
        "decisions": audit,
    }
    EVAL.mkdir(parents=True, exist_ok=True)
    (EVAL / "arxiv_id_resolution.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))

    print("\n=== Stage 0: arXiv-id resolution ===")
    for s in ("local", "searched", "unresolved", "no_arxiv_id", "search_error"):
        if counts.get(s):
            print(f"  {s:13s} {pct(counts[s], n)}")
    print(f"  {'RESOLVED':13s} {pct(resolved, n)}  (local+searched -> fetch universe)")
    print_status_by_cluster(recs, "openalex_id", "status", "no_arxiv_id",
                            "no_arxiv_id by cluster (concentrated = expected journal/bioRxiv):")
    print(f"  report -> {EVAL / 'arxiv_id_resolution.json'}")


if __name__ == "__main__":
    sys.exit(main())
