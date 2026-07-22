"""lab/dedupe_corpus.py — corpus dedupe by title+year (MANDATORY pre-re-cluster).

The v3 corpus holds the same paper under distinct OpenAlex Wids (e.g. LIME
twice: once as '"Why Should I Trust You?"', once with the full subtitle).
Measured cost: 29 of the 193 B\\A edges in the latex_refs compare are
duplicate-twin artifacts. This script collapses those records into a NEW
data/raw/interp_corpus_v4.jsonl — v3 is frozen (the current clustering /
layout / graph were built from it) and is never touched.

Detection tiers, never forced (candidates that fail a gate are logged
rejected, not merged):

  doi          same normalized DOI                     -> definite
  arxiv        same cleaned arXiv id                   -> definite
  title_exact  same norm(title), |year_diff| <= 1      -> author gate
  title_fuzzy  same year, token_set >= 0.92 AND
               (token_sort >= 0.85 OR strict token-subset either way — the
               truncated-title twin case)              -> author gate

Author gate, tiered by title evidence:
  - DISQUALIFIER first: two records carrying DIFFERENT arXiv ids are two
    different works, full stop — reject regardless of titles. (Distinct DOIs
    do NOT reject: LIME legitimately exists as KDD + NAACL-demo DOIs.)
  - sort >= 0.85 or exact title: >= 1 surname overlap suffices.
  - subset-only match (sort < 0.85): surname-set Jaccard >= 0.5. One shared
    surname is NOT enough — a generic subset title ('Editing Large Language
    Models') chains DISTINCT papers from one prolific group (Yao/Zhang) into
    a single false merge; near-identical author sets are what separates a
    true twin (LIME: identical) from labmates' sibling papers (~0.2).
A side with no authors passes vacuously (logged as such).

Merge policy (per union-find group):
  canonical  the record with the FULLEST title (most tokens), then most
             metadata (abstract/doi/arxiv), then most edges, then lowest Wid —
             deterministic. Fuller titles matter: truncated ones are exactly
             what broke title matching downstream.
  fields     canonical keeps its own; None/empty filled from twins
  edges      union of all group members', remapped corpus-wide
  cited_by_count  SUM across the group — OpenAlex split the citations
             between the twins, so neither twin's count alone is right
  _merged_from    the absorbed Wids, kept for provenance/remapping

After merging, EVERY record's edges are remapped (absorbed Wid -> canonical),
deduped order-preserving, self-edges dropped; _in_corpus_cites is recomputed
from the remapped edge set. Merge map (accepted + rejected, with scores) goes
to lab/eval/corpus_dedupe_map.json, human-readable audit to
lab/eval/corpus_dedupe_audit.md.

Usage:
  python -m lab.dedupe_corpus            # detect + audit only (no write)
  python -m lab.dedupe_corpus --apply    # also write interp_corpus_v4.jsonl
"""
import argparse
import json
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from rapidfuzz import fuzz

from lab.latex_refs.common import (EVAL, clean_arxiv, load_corpus, local_arxiv_id,
                                   norm, oa_key, pct, surnames)

ROOT = Path(__file__).resolve().parent.parent
OUT_V4 = ROOT / "data" / "raw" / "interp_corpus_v4.jsonl"

SET_MIN = 0.92
SORT_MIN = 0.85
YEAR_EXACT_TITLE = 1   # exact-title tier tolerates preprint/published drift


def norm_doi(d):
    if not d:
        return None
    d = str(d).strip().lower()
    for pre in ("https://doi.org/", "https://dx.doi.org/", "doi:"):
        if d.startswith(pre):
            d = d[len(pre):]
    return d.rstrip(".") or None


def author_gate(a, b, need_jaccard=False):
    """(passes, detail) — >=1 surname overlap, or Jaccard >= 0.5 for the
    weak-evidence (subset-only) tier; vacuous pass if a side lacks authors."""
    sa, sb = surnames(a.get("authors")), surnames(b.get("authors"))
    if not sa or not sb:
        return True, "vacuous (missing authors)"
    ov = sa & sb
    if need_jaccard:
        j = len(ov) / len(sa | sb)
        return j >= 0.5, f"jaccard={j:.2f} overlap={sorted(ov)[:3]}"
    return bool(ov), f"overlap={sorted(ov)[:3]}" if ov else "overlap=0"


def arxiv_conflict(a, b):
    """Two records with DIFFERENT arXiv ids are different works — hard reject."""
    ax_a, ax_b = local_arxiv_id(a), local_arxiv_id(b)
    return bool(ax_a and ax_b and ax_a != ax_b)


def find_candidates(recs):
    """All candidate pairs with tier + scores + accept/reject decision."""
    by_doi, by_arxiv, by_nt = defaultdict(list), defaultdict(list), defaultdict(list)
    by_year = defaultdict(list)
    for r in recs:
        w = oa_key(r)
        d = norm_doi(r.get("doi"))
        if d and not d.startswith("10.48550/arxiv"):   # arxiv DOIs handled by arxiv tier
            by_doi[d].append(w)
        ax = local_arxiv_id(r)
        if ax:
            by_arxiv[ax].append(w)
        nt = norm(r.get("title"))
        if nt:
            by_nt[nt].append(w)
        if r.get("year") and nt:
            by_year[r["year"]].append(w)
    rec = {oa_key(r): r for r in recs}
    nt_of = {oa_key(r): norm(r.get("title")) for r in recs}

    cands, seen = [], set()

    def add(w1, w2, tier, scores, weak_title=False):
        key = tuple(sorted((w1, w2)))
        if key in seen:
            return
        seen.add(key)
        if tier.startswith("title") and arxiv_conflict(rec[w1], rec[w2]):
            accepted, detail = False, "REJECT: distinct arXiv ids (different works)"
        elif tier.startswith("title"):
            accepted, detail = author_gate(rec[w1], rec[w2], need_jaccard=weak_title)
        else:
            accepted, detail = True, "identity tier"  # doi/arxiv definite
        cands.append({"pair": list(key), "tier": tier, "accepted": accepted,
                      "author_gate": detail, **scores,
                      "titles": [rec[key[0]].get("title"), rec[key[1]].get("title")],
                      "years": [rec[key[0]].get("year"), rec[key[1]].get("year")]})

    for d, ws in by_doi.items():
        for w1, w2 in combinations(sorted(ws), 2):
            add(w1, w2, "doi", {"doi": d})
    for ax, ws in by_arxiv.items():
        for w1, w2 in combinations(sorted(ws), 2):
            add(w1, w2, "arxiv", {"arxiv_id": ax})
    for nt, ws in by_nt.items():
        for w1, w2 in combinations(sorted(ws), 2):
            y1, y2 = rec[w1].get("year"), rec[w2].get("year")
            if y1 and y2 and abs(y1 - y2) <= YEAR_EXACT_TITLE:
                add(w1, w2, "title_exact", {"year_diff": abs(y1 - y2)})
    for y, ws in by_year.items():
        for w1, w2 in combinations(sorted(ws), 2):
            n1, n2 = nt_of[w1], nt_of[w2]
            if n1 == n2:
                continue                      # title_exact already saw it
            s_set = fuzz.token_set_ratio(n1, n2) / 100.0
            if s_set < SET_MIN:
                continue
            s_sort = fuzz.token_sort_ratio(n1, n2) / 100.0
            t1, t2 = set(n1.split()), set(n2.split())
            subset = t1 < t2 or t2 < t1
            if s_sort >= SORT_MIN or subset:
                add(w1, w2, "title_fuzzy",
                    {"title_set": round(s_set, 4), "title_sort": round(s_sort, 4),
                     "subset": subset},
                    weak_title=(s_sort < SORT_MIN))   # subset-only -> Jaccard gate
    return cands


def union_groups(pairs):
    """Union-find over accepted pairs -> list of merged-Wid groups (size >= 2)."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for w1, w2 in pairs:
        parent[find(w1)] = find(w2)
    groups = defaultdict(list)
    for w in parent:
        groups[find(w)].append(w)
    return [sorted(g) for g in groups.values() if len(g) >= 2]


def pick_canonical(group, rec):
    """Fullest title, then metadata richness, then edges, then lowest Wid."""
    def score(w):
        r = rec[w]
        return (-len(norm(r.get("title")).split()),
                -(1 if r.get("abstract") else 0),
                -(1 if r.get("doi") else 0),
                -(1 if local_arxiv_id(r) else 0),
                -len(r.get("edges") or []),
                w)  # lowest Wid as final deterministic tie-break
    return min(group, key=score)


def merge_and_rewrite(recs, groups):
    rec = {oa_key(r): r for r in recs}
    remap = {}
    for g in groups:
        canon = pick_canonical(g, rec)
        for w in g:
            if w != canon:
                remap[w] = canon
    out = []
    for r in recs:
        w = oa_key(r)
        if w in remap:
            continue
        r = dict(r)
        absorbed = [a for a, c in remap.items() if c == w]
        if absorbed:
            for a in absorbed:
                twin = rec[a]
                for f in ("abstract", "doi", "arxiv_id", "venue", "year"):
                    if not r.get(f) and twin.get(f):
                        r[f] = twin[f]
            r["cited_by_count"] = sum(rec[x].get("cited_by_count") or 0
                                      for x in [w] + absorbed)
            r["_merged_from"] = sorted(absorbed)
        merged_edges = list(r.get("edges") or [])
        for a in absorbed:
            merged_edges.extend(rec[a].get("edges") or [])
        seen, edges = set(), []
        for t in merged_edges:
            t = remap.get(t, t)
            if t != w and t not in seen:
                seen.add(t)
                edges.append(t)
        r["edges"] = edges
        out.append(r)
    # recompute _in_corpus_cites from the remapped edge set
    incoming = defaultdict(int)
    for r in out:
        for t in r["edges"]:
            incoming[t] += 1
    for r in out:
        r["_in_corpus_cites"] = incoming[oa_key(r)]
    return out, remap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="write interp_corpus_v4.jsonl (default: detect+audit only)")
    args = ap.parse_args()

    recs = load_corpus()
    rec = {oa_key(r): r for r in recs}
    cands = find_candidates(recs)
    accepted = [c for c in cands if c["accepted"]]
    rejected = [c for c in cands if not c["accepted"]]
    groups = union_groups([tuple(c["pair"]) for c in accepted])
    canon = {tuple(g): pick_canonical(g, rec) for g in groups}

    EVAL.mkdir(parents=True, exist_ok=True)
    (EVAL / "corpus_dedupe_map.json").write_text(json.dumps({
        "source": "data/raw/interp_corpus_v3_clean.jsonl",
        "n_records": len(recs),
        "candidates": cands,
        "groups": [{"members": g, "canonical": canon[tuple(g)]} for g in groups],
    }, indent=2, ensure_ascii=False))

    L = ["# corpus dedupe audit — title+year (pre-re-cluster mandate)\n",
         f"Source: v3 (683 records, frozen). Candidates: {len(cands)} "
         f"({len(accepted)} accepted, {len(rejected)} rejected by author gate). "
         f"Merge groups: {len(groups)}.\n",
         "## Accepted merges\n"]
    for g in sorted(groups):
        c = canon[tuple(g)]
        L.append(f"### {' + '.join(g)} -> keep `{c}`")
        for w in g:
            mark = " **<- canonical**" if w == c else ""
            L.append(f"- `{w}` ({rec[w].get('year')}, cited_by={rec[w].get('cited_by_count')}, "
                     f"edges={len(rec[w].get('edges') or [])}) "
                     f"{(rec[w].get('title') or '')[:90]}{mark}")
        tiers = [c2 for c2 in accepted if set(c2["pair"]) <= set(g)]
        for t in tiers:
            sc = {k: v for k, v in t.items()
                  if k in ("doi", "arxiv_id", "year_diff", "title_set", "title_sort", "subset")}
            L.append(f"  - via `{t['tier']}` {sc} author_gate: {t['author_gate']}")
        L.append("")
    L.append("## Rejected candidates (gate failed — kept separate, review these)\n")
    if not rejected:
        L.append("(none)")
    for t in rejected:
        L.append(f"- `{t['pair'][0]}` vs `{t['pair'][1]}` via `{t['tier']}` "
                 f"author_gate: {t['author_gate']}")
        L.append(f"  - “{(t['titles'][0] or '')[:80]}” ({t['years'][0]}) vs "
                 f"“{(t['titles'][1] or '')[:80]}” ({t['years'][1]})")
    L.append("")
    (EVAL / "corpus_dedupe_audit.md").write_text("\n".join(L))

    n_removed = sum(len(g) - 1 for g in groups)
    print(f"=== corpus dedupe (v3 -> v4) ===")
    print(f"  records          {len(recs)}")
    print(f"  candidate pairs  {len(cands)}  (accepted {len(accepted)}, rejected {len(rejected)})")
    print(f"  merge groups     {len(groups)}  -> records removed: {n_removed}")
    print(f"  audit -> {EVAL / 'corpus_dedupe_audit.md'}")
    print(f"  map   -> {EVAL / 'corpus_dedupe_map.json'}")

    if not args.apply:
        print("  (detect-only: re-run with --apply to write v4)")
        return

    out, remap = merge_and_rewrite(recs, groups)
    assert len(out) == len(recs) - n_removed
    live = {oa_key(r) for r in out}
    dangling = [(oa_key(r), t) for r in out for t in r["edges"] if t not in live and t in remap]
    assert not dangling, f"edges still point at removed Wids: {dangling[:5]}"
    with OUT_V4.open("w") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    n_edges = sum(len(r["edges"]) for r in out)
    print(f"  wrote {OUT_V4.name}: {pct(len(out), len(recs))} records kept, "
          f"{n_edges} edges after remap")


if __name__ == "__main__":
    sys.exit(main())
