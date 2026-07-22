"""lab/latex_refs/compare.py — Stage 5: our LaTeX citation index vs OpenAlex edges.

Two in-corpus edge sets over the same 683-paper corpus:

  A  latex   (citing -> cited) from Stage 3: references parsed out of arXiv
             e-print source, resolved through the eprint->doi->title chain
  B  openalex  the corpus records' own `edges` field (in-corpus OpenAlex
             citations), as ingested — entirely local, no network

HONEST DENOMINATOR: A only exists where we parsed source (431 papers). B is
therefore restricted to edges whose CITING paper is in that parse universe
before comparing — otherwise coverage difference masquerades as index
difference. B_full is still reported for context.

Buckets: both (A∩B), latex_only (A\\B), oa_only (B\\A). For oa_only, a
diagnosis pass probes each citing paper's UNMATCHED ref titles for the cited
paper's title (sim >= 0.85 -> likely a resolution miss on our side; below ->
the reference is plausibly absent from the .bbl, or the OpenAlex edge itself
is wrong). 10 deterministic, evenly-spaced audit samples per bucket go to
lab/eval/latex_refs_audit.md for human review.

Built so a third source (S2) slots in as another named edge set + pairwise
compare, without a refactor. Writes data/latex/compare.json + the audit md.

Usage:
  python -m lab.latex_refs.compare
"""
import json
import sys
from collections import Counter

from rapidfuzz import fuzz

from .common import EVAL, LATEX, load_corpus, norm, oa_key, pct
from .resolve import clean_ref_title, match_text

NEAR_MISS_SIM = 0.85


def load_edge_sets():
    """Returns (A, B_restricted, B_full, parsed_wids, per-edge method map)."""
    res_p = LATEX / "resolved.jsonl"
    if not res_p.exists():
        sys.exit("Stage 3 output missing: run resolve first (data/latex/resolved.jsonl).")
    resolved = [json.loads(l) for l in res_p.open() if l.strip()]
    parsed = {r["openalex_id"] for r in resolved}
    A, method = set(), {}
    for r in resolved:
        for m in r["matches"]:
            if m["status"] == "matched":
                e = (r["openalex_id"], m["corpus_id"])
                A.add(e)
                method.setdefault(e, (m["method"], m.get("key")))
    B_full = set()
    for rec in load_corpus():
        w = oa_key(rec)
        for tgt in rec.get("edges") or []:
            B_full.add((w, tgt))
    B_r = {e for e in B_full if e[0] in parsed}
    return A, B_r, B_full, parsed, method, resolved


def spaced_sample(edges, k=10):
    """Deterministic, evenly spaced sample across the sorted edge list."""
    edges = sorted(edges)
    if len(edges) <= k:
        return edges
    idx = sorted({round(i * (len(edges) - 1) / (k - 1)) for i in range(k)})
    return [edges[i] for i in idx]


def diagnose_oa_only(edges, resolved, titles):
    """For each B\\A edge: does the citing paper's UNMATCHED refs contain a
    near-miss of the cited title? Returns {edge: (best_sim, best_ref_title)}."""
    unmatched = {}
    refs_by_paper = {r["openalex_id"]: r for r in
                     (json.loads(l) for l in (LATEX / "refs.jsonl").open() if l.strip())}
    res_by_paper = {r["openalex_id"]: r for r in resolved}
    out = {}
    for citing, cited in edges:
        if citing not in unmatched:
            rr, rs = refs_by_paper.get(citing), res_by_paper.get(citing)
            pool = []
            if rr and rs:
                for m in rs["matches"]:
                    if m["status"] == "unmatched":
                        t = norm(match_text(clean_ref_title(rr["refs"][m["idx"]].get("title"))))
                        if t:
                            pool.append((t, rr["refs"][m["idx"]].get("title") or ""))
            unmatched[citing] = pool
        q = norm(match_text(titles.get(cited, "")))
        best, best_t = 0.0, ""
        for t, orig in unmatched[citing]:
            s = fuzz.token_set_ratio(q, t) / 100.0
            if s > best:
                best, best_t = s, orig
        out[(citing, cited)] = (round(best, 3), best_t[:80])
    return out


def main():
    A, B_r, B_full, parsed, method, resolved = load_edge_sets()
    corpus = load_corpus()
    titles = {oa_key(r): (r.get("title") or "")[:72] for r in corpus}

    both = A & B_r
    latex_only = A - B_r
    oa_only = B_r - A
    union = A | B_r

    by_method = Counter(method[e][0] for e in A)
    lo_method = Counter(method[e][0] for e in latex_only)
    diag = diagnose_oa_only(oa_only, resolved, titles)
    near = sum(1 for s, _ in diag.values() if s >= NEAR_MISS_SIM)

    report = {
        "citing_universe": f"{len(parsed)} source-parsed papers (of 683)",
        "n_A_latex": len(A),
        "n_B_openalex_restricted": len(B_r),
        "n_B_openalex_full": len(B_full),
        "both": len(both),
        "latex_only": len(latex_only),
        "oa_only": len(oa_only),
        "union": len(union),
        "A_by_method": dict(by_method),
        "latex_only_by_method": dict(lo_method),
        "oa_only_near_miss_in_unmatched_refs": near,
        "note": ("latex_only = edges our index sees that OpenAlex lacks; "
                 "oa_only near-miss count = how many look like OUR resolution "
                 "misses rather than absent references"),
    }
    (LATEX / "compare.json").write_text(json.dumps(report, indent=2))

    # ---- audit md ----------------------------------------------------------
    L = []
    L.append("# latex_refs audit — LaTeX citation index vs OpenAlex edges\n")
    L.append(f"Citing universe: **{len(parsed)} source-parsed papers** (of 683). "
             f"B restricted to this universe before comparing; B_full = {len(B_full)}.\n")
    L.append("| bucket | edges | share of union |")
    L.append("|---|---|---|")
    for name, s in (("A∩B (both)", both), ("A\\B (latex only)", latex_only),
                    ("B\\A (openalex only)", oa_only)):
        L.append(f"| {name} | {len(s)} | {pct(len(s), len(union))} |")
    L.append(f"| A∪B (union) | {len(union)} | — |")
    L.append("")
    L.append(f"A = {len(A)} (by method: {dict(by_method)}); "
             f"B_restricted = {len(B_r)}; B_full = {len(B_full)}.\n")
    L.append(f"Of the {len(oa_only)} openalex-only edges, **{near}** have a "
             f"near-miss (sim ≥ {NEAR_MISS_SIM}) among the citing paper's "
             f"unmatched refs — likely OUR resolution misses; the rest are "
             f"plausibly absent from the .bbl or wrong in OpenAlex.\n")

    def row(e, extra=""):
        c, t = e
        return (f"- `{c}` **{titles.get(c, '?')}** →\n  `{t}` "
                f"**{titles.get(t, '?')}**{extra}")

    L.append("## A∩B — 10 samples (both indexes agree)\n")
    for e in spaced_sample(both):
        meth, key = method[e]
        L.append(row(e, f"\n  via `{meth}`, key `{key}`"))
    L.append("\n## A\\B — 10 samples (we see it, OpenAlex doesn't — verify the ref is real)\n")
    for e in spaced_sample(latex_only):
        meth, key = method[e]
        L.append(row(e, f"\n  via `{meth}`, key `{key}`"))
    L.append("\n## B\\A — 10 samples (OpenAlex sees it, we don't — why?)\n")
    for e in spaced_sample(oa_only):
        s, t = diag[e]
        why = (f"near-miss in unmatched refs (sim={s}): “{t}”" if s >= NEAR_MISS_SIM
               else f"no similar unmatched ref (best sim={s}) — absent from .bbl or bad OA edge")
        L.append(row(e, f"\n  {why}"))
    L.append("")
    (EVAL / "latex_refs_audit.md").write_text("\n".join(L))

    print("=== Stage 5: compare (A=latex, B=openalex, citing universe = "
          f"{len(parsed)} parsed papers) ===")
    print(f"  A (latex)          {len(A)}   {dict(by_method)}")
    print(f"  B (openalex, restr){len(B_r)}   (full: {len(B_full)})")
    print(f"  A∩B both           {pct(len(both), len(union))} of union")
    print(f"  A\\B latex_only     {pct(len(latex_only), len(union))} of union")
    print(f"  B\\A oa_only        {pct(len(oa_only), len(union))} of union"
          f"   ({near} look like our resolution misses)")
    print(f"  audit -> {EVAL / 'latex_refs_audit.md'}")
    print(f"  json  -> {LATEX / 'compare.json'}")


if __name__ == "__main__":
    sys.exit(main())
