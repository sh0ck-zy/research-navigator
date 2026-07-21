"""ingest_v3.py — interp corpus via OpenAlex-only forward+backward snowball.

No Semantic Scholar (avoids the 429 wall). OpenAlex polite pool via --mailto.

Pipeline:
  1. seeds    — resolve iconic interp papers (arXiv IDs) → OpenAlex works
  2. expand   — BACKWARD (referenced_works of seeds) + FORWARD (works that cite
                the seeds, via filter=cites:W1|W2|...), then one forward hop from
                the strongest interp papers
  3. graph    — build the in-corpus citation graph over all candidates
  4. filter   — LABEL PROPAGATION from seed labels + keyword prior over the
                citation graph (generic-DL background like ResNet has a diluted
                neighbourhood → low interp score → dropped), keep high scorers
  5. export   — JSONL with real in-corpus edges + `year`. Reserved-for-later
                (S2 / L3): influential_citations, CITES.intent/contexts.

Everything is checkpointed under data/raw/.ckpt_v3/ (Ctrl-C safe).

Usage:
  python backend/pipeline/ingest_v3.py --mailto you@x.com [--stats]
"""
import argparse
import json
import re
import time
from collections import defaultdict
from pathlib import Path

import requests

OPENALEX = "https://api.openalex.org/works"

# ── Iconic interp seeds — the anchor set labelled interp=1.0 ──
# (arxiv_id, expected_title, expected_year). Title+year are VERIFIED on every
# resolution: OpenAlex's arXiv-DOI index is unreliable and silently returns the
# wrong work (~3/17 in run 1), which then poisons forward citation expansion.
SEEDS = [
    ("2209.11895", "In-context Learning and Induction Heads", 2022),
    ("2209.10652", "Toy Models of Superposition", 2022),
    ("2211.00593", "Interpretability in the Wild: a Circuit for Indirect Object Identification in GPT-2 small", 2022),
    ("2202.05262", "Locating and Editing Factual Associations in GPT", 2022),
    ("2309.08600", "Sparse Autoencoders Find Highly Interpretable Features in Language Models", 2023),
    ("2301.05217", "Progress measures for grokking via mechanistic interpretability", 2023),
    ("2210.13382", "Emergent World Representations: Exploring a Sequence Model Trained on a Synthetic Task", 2022),
    ("2310.01405", "Representation Engineering: A Top-Down Approach to AI Transparency", 2023),
    ("2311.03658", "The Linear Representation Hypothesis and the Geometry of Large Language Models", 2023),
    ("2403.19647", "Sparse Feature Circuits: Discovering and Editing Interpretable Causal Graphs in Language Models", 2024),
    ("2012.14913", "Transformer Feed-Forward Layers Are Key-Value Memories", 2020),
    ("2306.03341", "Inference-Time Intervention: Eliciting Truthful Answers from a Language Model", 2023),
    ("2310.06824", "The Geometry of Truth: Emergent Linear Structure in Large Language Model Representations of True/False Datasets", 2023),
    ("2405.14860", "Scaling and evaluating sparse autoencoders", 2024),
    ("2408.05147", "Gemma Scope: Open Sparse Autoencoders Everywhere All At Once on Gemma 2", 2024),
    ("1704.01444", "Learning to Generate Reviews and Discovering Sentiment", 2017),
    ("2401.06102", "Patchscopes: A Unifying Framework for Inspecting Hidden Representations of Language Models", 2024),
    ("2304.14767", "Analyzing Transformers in Embedding Space", 2022),
]

CORE_KEYWORDS = [
    "mechanistic interpretab", "sparse autoencoder", "superposition",
    "activation patching", "attribution patching", "circuit discovery",
    "transformer circuit", "interpretab", "probing", "probe classifier",
    "feature visualization", "dictionary learning", "monosemantic",
    "polysemantic", "induction head", "residual stream", "activation steering",
    "representation engineering", "steering vector", "latent knowledge",
    "logit lens", "tuned lens", "patchscopes", "causal tracing",
    "causal scrubbing", "path patching", "attention head", "sae ",
    "transcoder", "crosscoder", "linear representation", "grokking",
    "knowledge editing", "model editing", "concept erasure",
]
STRONG_KEYWORDS = [
    "mechanistic interpretab", "sparse autoencoder", "superposition",
    "activation patching", "attribution patching", "induction head",
    "residual stream", "monosemantic", "transcoder", "crosscoder",
    "logit lens", "activation steering", "steering vector",
    "dictionary learning", "path patching", "causal scrubbing",
]

MIN_YEAR = 2014
FIELDS = ("id,doi,title,publication_year,cited_by_count,authorships,"
          "abstract_inverted_index,referenced_works,primary_location")


def norm_title(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def title_matches(expected, got):
    """True if `got` is the same paper as `expected` — tolerant of subtitle
    truncation ('Interpretability in the Wild' vs the full title) and of
    punctuation/casing, but not of a different paper."""
    a, b = norm_title(expected), norm_title(got)
    if not a or not b:
        return False
    if a == b or a.startswith(b) or b.startswith(a):
        return True
    ta, tb = set(a.split()), set(b.split())
    return len(ta & tb) / max(1, len(ta | tb)) >= 0.6


def reconstruct_abstract(inv):
    if not inv:
        return ""
    pos = [(p, w) for w, ps in inv.items() for p in ps]
    pos.sort()
    return " ".join(w for _, w in pos)


def normalize(w):
    authors = [a["author"]["display_name"] for a in (w.get("authorships") or [])
               if a.get("author", {}).get("display_name")]
    loc = w.get("primary_location") or {}
    venue = (loc.get("source") or {}).get("display_name")
    landing = loc.get("landing_page_url") or ""
    arxiv_id = landing.rstrip("/").split("/")[-1] if "arxiv.org" in landing else None
    return {
        "id": w["id"].replace("https://openalex.org/", ""),
        "arxiv_id": arxiv_id,
        "doi": (w.get("doi") or "").replace("https://doi.org/", "") or None,
        "title": w.get("title") or "Untitled",
        "authors": authors,
        "year": w.get("publication_year"),
        "venue": venue,
        "cited_by_count": w.get("cited_by_count", 0),
        "abstract": reconstruct_abstract(w.get("abstract_inverted_index")),
        "referenced_works": [r.replace("https://openalex.org/", "")
                             for r in (w.get("referenced_works") or [])],
    }


class OpenAlex:
    def __init__(self, mailto=None):
        self.s = requests.Session()
        self.p = {"mailto": mailto} if mailto else {}

    def _get(self, params):
        params = {**params, **self.p}
        for attempt in range(6):
            try:
                r = self.s.get(OPENALEX, params=params, timeout=60)
                if r.status_code == 429:
                    wait = min(2 ** attempt * 3, 60)
                    print(f"  [429] {wait}s..."); time.sleep(wait); continue
                r.raise_for_status()
                return r.json()
            except requests.RequestException as e:
                print(f"  [net] {e}; retry"); time.sleep(3)
        raise RuntimeError("OpenAlex unreachable")

    def resolve_seed(self, ax, want_title, want_year, year_tol=3):
        """arXiv id → OpenAlex work(s), TITLE-VERIFIED.

        1. try the DataCite arXiv DOI; accept only if the title matches.
        2. else fall back to a title search and accept only verified matches.

        Returns (primary, alts, info). OpenAlex frequently stores a paper twice
        (preprint record + published record) — `alts` holds the other verified
        versions so forward-citation expansion doesn't miss citers that point at
        the version we didn't pick.
        """
        info = {"arxiv_id": ax, "want_title": want_title, "via": None,
                "doi_lookup_title": None, "doi_lookup_ok": None,
                "resolved_title": None, "resolved_year": None,
                "year_ok": None, "n_versions": 0, "title_repaired": False}

        cands, via, doi_fallback = [], None, None
        d = self._get({"filter": f"doi:10.48550/arxiv.{ax}", "select": FIELDS})
        res = d.get("results", [])
        if res:
            info["doi_lookup_title"] = res[0].get("title")
        hit = next((r for r in res if title_matches(want_title, r.get("title"))), None)
        info["doi_lookup_ok"] = bool(hit) if res else False
        if hit:
            cands, via = [hit], "doi"
        else:
            # the arXiv DOI is a 1:1 identifier, so a DOI hit IS the right work even
            # when OpenAlex's display_name is corrupted (a junk metadata source has
            # overwritten titles/abstracts on some records — authors and citation
            # edges survive). Prefer a cleanly-titled record if one exists, else
            # take the DOI record and repair its title from our ground truth.
            doi_fallback = res[0] if res else None
            q = re.sub(r"[^A-Za-z0-9 ]+", " ", want_title).strip()
            d = self._get({"filter": f"title.search:{q}", "per_page": 25, "select": FIELDS})
            cands = [r for r in d.get("results", []) if title_matches(want_title, r.get("title"))]
            via = "title_search"
            if not cands and doi_fallback is not None:
                doi_fallback = {**doi_fallback, "title": want_title}
                cands, via = [doi_fallback], "doi_title_repaired"
                info["title_repaired"] = True

        if not cands:
            info["via"] = "MISS"
            return None, [], info

        cands.sort(key=lambda w: -(w.get("cited_by_count") or 0))
        primary = cands[0]
        info.update(via=via, resolved_title=primary.get("title"),
                    resolved_year=primary.get("publication_year"),
                    n_versions=len(cands))
        y = primary.get("publication_year")
        info["year_ok"] = bool(y and abs(y - want_year) <= year_tol)
        return primary, cands[1:4], info

    def by_ids(self, oa_ids):
        out = []
        for i in range(0, len(oa_ids), 50):
            chunk = "|".join(oa_ids[i:i + 50])
            d = self._get({"filter": f"openalex_id:{chunk}", "per_page": 50, "select": FIELDS})
            out += d.get("results", [])
            time.sleep(0.12)
        return out

    def citing(self, oa_ids, cap=20000):
        """Forward citations: works that cite ANY of oa_ids (filter=cites:OR)."""
        out = []
        for i in range(0, len(oa_ids), 40):
            chunk = "|".join(oa_ids[i:i + 40])
            cursor = "*"
            while cursor and len(out) < cap:
                d = self._get({"filter": f"cites:{chunk}", "per_page": 200,
                               "select": FIELDS, "cursor": cursor})
                out += d.get("results", [])
                cursor = (d.get("meta") or {}).get("next_cursor")
                time.sleep(0.12)
        return out


def kw(title, abstract):
    t = (title + " " + abstract).lower()
    return sum(1 for k in CORE_KEYWORDS if k in t), any(k in t for k in STRONG_KEYWORDS)


def ckpt(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))
    print(f"  [ckpt] {path.name} ({len(obj)})")


def label_propagation(works, seed_ids, alpha=0.55, iters=6):
    """Interp score per paper: blend of keyword prior + neighbourhood interp mass
    over the in-corpus citation graph. Seeds pinned to 1.0."""
    ids = [w["id"] for w in works]
    pool = set(ids)
    nbrs = defaultdict(set)
    for w in works:
        for r in w["referenced_works"]:
            if r in pool:
                nbrs[w["id"]].add(r)
                nbrs[r].add(w["id"])
    prior = {}
    for w in works:
        hits, strong = kw(w["title"], w["abstract"])
        prior[w["id"]] = 1.0 if strong else min(0.6, 0.25 * hits)
    score = dict(prior)
    for s in seed_ids:
        if s in score:
            score[s] = 1.0
    for _ in range(iters):
        nxt = {}
        for pid in ids:
            if pid in seed_ids:
                nxt[pid] = 1.0; continue
            ns = nbrs[pid]
            neigh = sum(score[n] for n in ns) / len(ns) if ns else 0.0
            nxt[pid] = alpha * prior[pid] + (1 - alpha) * neigh
        score = nxt
    return score, prior


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/raw/interp_corpus_v3.jsonl")
    ap.add_argument("--ckpt-dir", default="data/raw/.ckpt_v3")
    ap.add_argument("--mailto", default=None)
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--keep-threshold", type=float, default=0.34)
    ap.add_argument("--forward-cap", type=int, default=16000)
    ap.add_argument("--found-min", type=int, default=4,
                    help="a work referenced by >= this many forward citers is 'foundational'")
    ap.add_argument("--found-cap", type=int, default=4000)
    args = ap.parse_args()

    oa = OpenAlex(args.mailto)
    ck = Path(args.ckpt_dir)

    # 1 · seeds (title-verified)
    sp = ck / "seeds.json"
    rp = ck / "seed_resolution.json"
    if sp.exists():
        seeds = json.loads(sp.read_text())
    else:
        print("[1] resolving seeds via OpenAlex (title+year verified)...")
        seeds, resolution = [], []
        for ax, want_title, want_year in SEEDS:
            primary, alts, info = oa.resolve_seed(ax, want_title, want_year)
            resolution.append(info)
            if primary:
                seeds.append(normalize(primary))
                seeds += [normalize(a) for a in alts]
                flag = {"doi": "ok ", "title_search": "FIX",
                        "doi_title_repaired": "RPR"}[info["via"]]
                extra = "" if info["n_versions"] == 1 else f" (+{info['n_versions']-1} versions)"
                warn = "" if info["year_ok"] else f"  !! year {info['resolved_year']} vs want {want_year}"
                print(f"  {flag} {ax}  {info['resolved_title'][:58]}{extra}{warn}")
                if info["via"] != "doi":
                    print(f"       DOI lookup had returned: {info['doi_lookup_title']}")
            else:
                print(f"  MISS {ax}  {want_title[:50]}")
            time.sleep(0.2)
        # dedupe (alt versions can collide across seeds)
        seeds = list({w["id"]: w for w in seeds}.values())
        ckpt(sp, seeds)
        rp.write_text(json.dumps(resolution, indent=2))
        n_fix = sum(1 for r in resolution if r["via"] == "title_search")
        n_rpr = sum(1 for r in resolution if r["via"] == "doi_title_repaired")
        n_miss = sum(1 for r in resolution if r["via"] == "MISS")
        n_yr = sum(1 for r in resolution if r["year_ok"] is False)
        print(f"[1] resolution: {n_fix} rescued by title search, {n_rpr} title-repaired, "
              f"{n_miss} missing, {n_yr} year-mismatched → {rp.name}")
    seed_ids = [w["id"] for w in seeds]
    print(f"[1] {len(seeds)} seed records for {len(SEEDS)} seed papers")

    # 2 · expand (backward refs of seeds + forward citers of seeds)
    cp = ck / "candidates.json"
    if cp.exists():
        works = json.loads(cp.read_text())
        print(f"[2] candidates cached ({len(works)})")
    else:
        from collections import Counter
        back_ids = sorted({r for w in seeds for r in w["referenced_works"]})
        print(f"[2a] backward: {len(back_ids)} seed refs")
        back = [normalize(w) for w in oa.by_ids(back_ids)] if back_ids else []
        print(f"[2b] forward: citers of {len(seed_ids)} seeds (cap {args.forward_cap})...")
        fwd = [normalize(w) for w in oa.citing(seed_ids, cap=args.forward_cap)]
        print(f"      forward returned {len(fwd)}")
        # 2c · foundational: works the forward citers reference most (captures the
        #      older landmarks that arXiv-only seeds don't list as references)
        rc = Counter(r for w in fwd for r in w["referenced_works"])
        have = {w["id"] for w in seeds + back + fwd}
        found_ids = [wid for wid, c in rc.most_common()
                     if c >= args.found_min and wid not in have][:args.found_cap]
        print(f"[2c] foundational: {len(found_ids)} works referenced by >= {args.found_min} citers")
        found = [normalize(w) for w in oa.by_ids(found_ids)] if found_ids else []
        # merge + dedupe
        by_id = {}
        for w in seeds + back + fwd + found:
            by_id[w["id"]] = w
        works = list(by_id.values())
        ckpt(cp, works)

    # basic hygiene
    works = [w for w in works if w["abstract"] and w["year"] and w["year"] >= MIN_YEAR]
    print(f"[2] {len(works)} candidates after abstract/year hygiene")

    # 3+4 · in-corpus cites + label propagation filter
    pool = {w["id"] for w in works}
    icc = {w["id"]: 0 for w in works}
    for w in works:
        for r in w["referenced_works"]:
            if r in icc:
                icc[r] += 1
    score, prior = label_propagation(works, set(seed_ids))
    kept = []
    for w in works:
        hits, strong = kw(w["title"], w["abstract"])
        w["_kw_hits"] = hits
        w["_in_corpus_cites"] = icc[w["id"]]
        w["_interp_score"] = round(score[w["id"]], 4)
        if w["id"] in seed_ids or strong or score[w["id"]] >= args.keep_threshold:
            kept.append(w)
    kept.sort(key=lambda w: -w["_in_corpus_cites"])

    # in-corpus edges for the kept set
    kept_ids = {w["id"] for w in kept}
    n_edges = sum(1 for w in kept for r in w["referenced_works"] if r in kept_ids)

    # ── REPORT ──
    from collections import Counter
    years = dict(sorted(Counter(w["year"] for w in kept).items()))
    venues = Counter((w["venue"] or "?") for w in kept).most_common(6)
    n1 = sum(1 for w in kept if w["_in_corpus_cites"] >= 1 or any(r in kept_ids for r in w["referenced_works"]))
    print("\n==== REPORT ====")
    print(f"kept papers:            {len(kept)}  (from {len(works)} candidates)")
    print(f"in-corpus edges:        {n_edges}  (avg {n_edges/max(len(kept),1):.1f}/paper)")
    print(f"papers with >=1 edge:   {n1}  ({100*n1/max(len(kept),1):.0f}%)")
    print(f"years:                  {years}")
    print(f"top venues:             {venues}")
    print("================\n")

    if args.stats:
        return

    # 5 · export
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for w in kept:
            w["edges"] = [r for r in w["referenced_works"] if r in kept_ids]
            w.pop("referenced_works", None)
            f.write(json.dumps(w) + "\n")
    print(f"[5] wrote {out} — {len(kept)} papers")


if __name__ == "__main__":
    main()
