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

Second pass (--second-pass): re-tries ONLY the no_arxiv_id / unresolved /
search_error papers with wider queries — subtitle-stripped phrase, all-fields
phrase, AND-of-title-words — pooled and verified through the IDENTICAL gate.
How we search grows; what we accept does not. Each paper is marked
second_pass=true in its ckpt so a resumed run never re-queries it.

Usage:
  python -m lab.latex_refs.resolve_ids                 # full run (resumable)
  python -m lab.latex_refs.resolve_ids --limit 20      # smoke test
  python -m lab.latex_refs.resolve_ids --no-search     # local pass only
  python -m lab.latex_refs.resolve_ids --second-pass   # wider-search retry
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


def _arxiv_api(search_query, max_results=10, retries=3):
    """One arXiv api/query call with a pre-encoded search_query. Returns list
    of candidate dicts (arxiv_id, title, authors, year). Raises after retries."""
    url = f"{ARXIV_API}?search_query={search_query}&start=0&max_results={max_results}"
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


def arxiv_search(title):
    """First-pass search: exact-phrase title query, as run over the full corpus."""
    q = norm(title)
    if not q:
        return []
    return _arxiv_api(f'ti:%22{quote(q)}%22')


# Second pass: WIDER search, IDENTICAL gate. Query variants tried in order,
# each paced; candidates pooled and deduped, then verified with the exact same
# title_sim/author/year gate as pass one — recall may grow, precision may not drop.
_STOP = {"the", "a", "an", "of", "for", "and", "or", "in", "on", "with", "to",
         "from", "by", "at", "is", "are", "via", "as"}


def second_pass_queries(title):
    """[(label, search_query, max_results)] — subtitle-stripped phrase, all-fields
    phrase, then unphrased AND-of-title-words (broadest, gate does the filtering).
    HTML entities are unescaped first: corpus titles carry '&amp;' etc., which
    norm() would otherwise turn into a junk 'amp' token inside every query."""
    import html
    title = html.unescape(title or "")
    t = norm(title)
    out = []
    if ":" in (title or ""):
        head = norm(title.split(":")[0])
        if head and head != t and len(head.split()) >= 3:
            out.append(("ti_head", f'ti:%22{quote(head)}%22', 10))
    out.append(("all_phrase", f'all:%22{quote(t)}%22', 10))
    words = [w for w in t.split() if w not in _STOP][:8]
    if len(words) >= 3:
        out.append(("ti_words", "+AND+".join(f"ti:{quote(w)}" for w in words), 25))
    return out


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


def process_second(rec, prev):
    """Second pass over a previously-missed paper: pooled wider-query candidates,
    same gate. Updates the ckpt in place; never downgrades a resolved status."""
    wid = oa_key(rec)
    base = {"openalex_id": wid, "title": rec.get("title"), "year": rec.get("year")}
    pool, seen, errors = [], set(), []
    for label, sq, mr in second_pass_queries(rec.get("title")):
        time.sleep(PACE)
        try:
            for c in _arxiv_api(sq, max_results=mr):
                if c["arxiv_id"] and c["arxiv_id"] not in seen:
                    seen.add(c["arxiv_id"])
                    pool.append((label, c))
        except Exception as ex:  # noqa: BLE001
            errors.append(f"{label}: {str(ex)[:120]}")
    if not pool:
        status = "search_error" if errors and prev.get("status") == "search_error" else \
                 prev.get("status", "no_arxiv_id")
        return {**base, "status": status, "method": "search2", "arxiv_id": None,
                "verify": prev.get("verify"), "candidate": prev.get("candidate"),
                "n_candidates": 0, "second_pass": True,
                **({"error": "; ".join(errors)} if errors else {})}
    scored = sorted(((verify(rec, c), label, c) for label, c in pool),
                    key=lambda x: x[0][0]["title_sim"], reverse=True)
    (best_scores, passed), label, best = scored[0]
    cand_view = {k: best.get(k) for k in ("arxiv_id", "title", "authors", "year")}
    if passed:
        return {**base, "status": "searched", "method": "search2", "arxiv_id": best["arxiv_id"],
                "verify": best_scores, "candidate": cand_view,
                "n_candidates": len(pool), "second_pass": True, "query": label}
    return {**base, "status": "unresolved", "method": "search2", "arxiv_id": None,
            "verify": best_scores, "candidate": cand_view,
            "n_candidates": len(pool), "second_pass": True, "query": label}


SECOND_PASS_TARGETS = ("no_arxiv_id", "unresolved", "search_error")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="process at most N papers")
    ap.add_argument("--no-search", action="store_true", help="local pass only, no arXiv calls")
    ap.add_argument("--force", action="store_true", help="ignore existing checkpoints")
    ap.add_argument("--second-pass", action="store_true",
                    help="re-try only no_arxiv_id/unresolved/search_error papers "
                         "with wider queries (same verification gate)")
    args = ap.parse_args()

    corpus = load_corpus()
    if args.limit:
        corpus = corpus[: args.limit]

    if args.second_pass:
        targets = []
        for rec in corpus:
            prev = load_ckpt(STAGE, oa_key(rec))
            if prev and prev.get("status") in SECOND_PASS_TARGETS \
                    and not prev.get("second_pass"):   # resume: skip already re-tried
                targets.append((rec, prev))
        total = len(targets)
        print(f"second pass over {total} previously-missed papers "
              f"(gate unchanged: ts>={TITLE_MIN}, ov>=1, |yd|<={YEAR_MAX})")
        found = 0
        for i, (rec, prev) in enumerate(targets, 1):
            res = process_second(rec, prev)
            save_ckpt(STAGE, oa_key(rec), res)
            if res["status"] == "searched":
                found += 1
            v = res.get("verify") or {}
            print(f"[{i}/{total}] {res['openalex_id']} {res['status']}"
                  f"{' -> ' + res['arxiv_id'] if res.get('arxiv_id') else ''}"
                  f"  ts={v.get('title_sim')} ov={v.get('author_overlap')} "
                  f"yd={v.get('year_diff')} ({res.get('query', '-')})", flush=True)
        print(f"\nsecond pass: {found}/{total} newly resolved")
        write_reports()
        return

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
