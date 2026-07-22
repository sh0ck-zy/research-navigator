"""lab/latex_refs/resolve.py — Stage 3: resolve parsed references to corpus ids.

Each parsed reference (Stage 2) is matched against the 683-paper corpus through
a fixed chain — first hit wins, per the workstream contract, never forced:

  1. eprint   an arXiv id in the entry hits the Stage-0 resolved map
              (442 corpus papers with an arXiv id — local + gate-passed search)
  2. doi      normalized DOI equality against the corpus record
  3. title    title_sim >= 0.92 (token_set_ratio) AND title_sort >= 0.85
              (token_sort_ratio co-gate) AND |year_diff| <= 2 — year REQUIRED
              on both sides; a ref with no year can only match via eprint/doi.
              The match query is the ref title with leading URL/DOI junk and
              trailing dates stripped; set-ratio alone force-matched subset
              titles to different papers, the sort co-gate kills those.
              Near-misses (set passed, sort failed) are logged for audit.
              Quote characters (straight/curly/guillemets/TeX backticks) and
              leading URLs are stripped from BOTH sides before scoring —
              formatting must never masquerade as absence (the B\\A recall fix).

Anything that fails the whole chain stays status=unmatched with its raw kept
(refs.jsonl still has the full entry). A match to the citing paper itself is
status=self and never becomes an edge.

All local — no network. Reads refs.jsonl + ids.jsonl + corpus; one ckpt per
paper; folds to data/latex/resolved.jsonl.

Usage:
  python -m lab.latex_refs.resolve                 # full run (resumable)
  python -m lab.latex_refs.resolve --limit 20      # smoke test
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict

from rapidfuzz import fuzz

from .common import (LATEX, aggregate, load_ckpt, load_corpus, norm, oa_key, pct,
                     save_ckpt, title_sim)

STAGE = "resolve"
TITLE_MIN = 0.92     # token_set_ratio — robust to word order / subtitle drops
SORT_MIN = 0.85      # token_sort_ratio co-gate — kills subset-title matches to a
                     # DIFFERENT paper ('Post-hoc Concept Bottleneck Models' vs
                     # 'Concept Bottleneck Models'), which set-ratio alone accepts.
                     # Stage 0 had the author gate for this; bib entries don't.
YEAR_MAX = 2

DOI_PREFIX = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)\s*", re.I)

# Ref titles from Stage 2 sometimes carry junk that tanks token_sort on REAL
# matches: leading URLs/DOIs ('https://aclanthology.org/P19-1580 Analyzing ...')
# and trailing dates ('Toy models of superposition, Sep 2022'). Strip both from
# the MATCH QUERY only — the stored title stays verbatim.
_URLISH = re.compile(r"^(?:(?:https?://|www\.)\S+|doi:?\S+|10\.\d{4,9}/\S+)\s*", re.I)
_MONTHS = (r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?"
           r"|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?")
_TAIL_DATE = re.compile(rf"[,.;]?\s*(?:{_MONTHS})?\.?\s*(?:19|20)\d\d[a-z]?\s*$", re.I)


def clean_ref_title(t):
    t = (t or "").strip()
    while True:
        t2 = _URLISH.sub("", t).strip()
        if t2 == t:
            break
        t = t2
    return _TAIL_DATE.sub("", t).strip()


# Quote characters — straight, curly, guillemets, TeX backticks — are STRIPPED
# (not spaced) before scoring, ON BOTH SIDES: '“Why Should I Trust You?”' must
# meet '"Why Should I Trust You?"' as the same tokens, and possessives must not
# split ("it's" -> "its", not "it s"). Leading URLs likewise on both sides.
_QUOTES = "\"'“”‘’«»‹›„‟`´"
_QUOTE_TABLE = str.maketrans("", "", _QUOTES)
_LEAD_URL = re.compile(r"^(?:https?://\S+\s+)+", re.I)


def match_text(t):
    """Title text as used for similarity scoring — applied to ref AND corpus."""
    return _LEAD_URL.sub("", (t or "").strip()).translate(_QUOTE_TABLE)


def norm_doi(d):
    if not d:
        return None
    d = DOI_PREFIX.sub("", str(d).strip()).lower().rstrip(".")
    return d or None


def build_indexes():
    """Corpus lookup tables: arxiv->Wid (Stage-0 resolved map), doi->Wid,
    and per-year title buckets for the gated title step."""
    corpus = load_corpus()
    by_arxiv, by_doi = {}, {}
    by_year = defaultdict(list)  # year -> [(Wid, norm_title, year)]
    ids_p = LATEX / "ids.jsonl"
    if not ids_p.exists():
        sys.exit("Stage 0 output missing: run resolve_ids first (data/latex/ids.jsonl).")
    for line in ids_p.open():
        r = json.loads(line)
        if r["status"] in ("local", "searched") and r.get("arxiv_id"):
            by_arxiv[r["arxiv_id"]] = r["openalex_id"]
    for rec in corpus:
        wid = oa_key(rec)
        d = norm_doi(rec.get("doi"))
        if d:
            by_doi[d] = wid
        if rec.get("year"):
            by_year[rec["year"]].append((wid, norm(match_text(rec.get("title"))), rec["year"]))
    return by_arxiv, by_doi, by_year


def resolve_ref(ref, by_arxiv, by_doi, by_year):
    """One reference through the chain. Returns (status, corpus_id, method, extra)."""
    for ax in ref.get("arxiv_ids") or []:
        if ax in by_arxiv:
            return "matched", by_arxiv[ax], "eprint", {"arxiv_id": ax}
    d = norm_doi(ref.get("doi"))
    if d and d in by_doi:
        return "matched", by_doi[d], "doi", {"doi": d}
    ry = ref.get("year")
    q = norm(match_text(clean_ref_title(ref.get("title"))))
    if ry and q:
        best, best_sim = None, 0.0
        for y in range(ry - YEAR_MAX, ry + YEAR_MAX + 1):
            for wid, nt, cy in by_year.get(y, ()):
                s = title_sim(q, nt)
                if s > best_sim:
                    best, best_sim = (wid, nt, cy), s
        if best and best_sim >= TITLE_MIN:
            srt = fuzz.token_sort_ratio(q, best[1]) / 100.0
            yd = abs(ry - best[2])
            # Strict-subset trap: ref 'Emergent Abilities of LLMs' (Wei 2022)
            # set-matches 'Are Emergent Abilities of LLMs a Mirage?' (2023) —
            # the ref is missing the DISTINCTIVE tokens. When the ref title is a
            # strict subset of the corpus title (>=2 extra corpus tokens), the
            # years must agree exactly; string similarity cannot separate these.
            qt, ct = set(q.split()), set(best[1].split())
            subset_trap = qt < ct and len(ct - qt) >= 2 and yd != 0
            if srt >= SORT_MIN and not subset_trap:
                return "matched", best[0], "title", {"title_sim": round(best_sim, 4),
                                                     "title_sort": round(srt, 4),
                                                     "year_diff": yd}
            reason = "subset_year" if (srt >= SORT_MIN) else "sort_gate"
            return "unmatched", None, None, {"near_miss": {"corpus_id": best[0],
                                                           "title_sim": round(best_sim, 4),
                                                           "title_sort": round(srt, 4),
                                                           "reason": reason}}
    return "unmatched", None, None, {}


def process(paper, by_arxiv, by_doi, by_year):
    wid = paper["openalex_id"]
    out = []
    for i, ref in enumerate(paper.get("refs") or []):
        status, cid, method, extra = resolve_ref(ref, by_arxiv, by_doi, by_year)
        if status == "matched" and cid == wid:
            status, cid, method = "self", None, method
        out.append({"idx": i, "key": ref.get("key"), "status": status,
                    "corpus_id": cid, "method": method, **extra})
    n_matched = sum(1 for r in out if r["status"] == "matched")
    return {"openalex_id": wid, "n_refs": len(out), "n_matched": n_matched,
            "matches": out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    refs_p = LATEX / "refs.jsonl"
    if not refs_p.exists():
        sys.exit("Stage 2 output missing: run parse_refs first (data/latex/refs.jsonl).")
    papers = [json.loads(l) for l in refs_p.open() if l.strip()]
    if args.limit:
        papers = papers[: args.limit]
    total = len(papers)

    by_arxiv, by_doi, by_year = build_indexes()
    print(f"indexes: {len(by_arxiv)} arxiv ids, {len(by_doi)} dois, "
          f"{sum(len(v) for v in by_year.values())} titled+dated corpus records")

    for i, paper in enumerate(papers, 1):
        wid = paper["openalex_id"]
        if not args.force and load_ckpt(STAGE, wid):
            continue
        res = process(paper, by_arxiv, by_doi, by_year)
        save_ckpt(STAGE, wid, res)
        print(f"[{i}/{total}] {wid} matched={res['n_matched']}/{res['n_refs']}", flush=True)

    write_reports()


def write_reports():
    recs = aggregate(STAGE, "resolved.jsonl")
    n_refs = sum(r["n_refs"] for r in recs)
    by_status = Counter(m["status"] for r in recs for m in r["matches"])
    by_method = Counter(m["method"] for r in recs for m in r["matches"]
                        if m["status"] == "matched")
    edges = {(r["openalex_id"], m["corpus_id"]) for r in recs
             for m in r["matches"] if m["status"] == "matched"}
    print("\n=== Stage 3: reference resolution (to the 683 corpus) ===")
    print(f"  papers            {len(recs)}")
    print(f"  references        {n_refs}")
    print(f"  matched           {pct(by_status['matched'], n_refs)}"
          f"   (most refs cite OUTSIDE the corpus — expected)")
    for meth, c in by_method.most_common():
        print(f"    via {meth:7s}   {c}")
    print(f"  self              {by_status['self']}")
    print(f"  unmatched (raw kept) {by_status['unmatched']}")
    print(f"  DISTINCT in-corpus edges A: {len(edges)}")


if __name__ == "__main__":
    sys.exit(main())
