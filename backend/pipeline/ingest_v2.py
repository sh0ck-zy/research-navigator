"""
ingest_v2.py — Build the mechanistic interpretability corpus (ADR-011).

Strategy: seed from the reference lists of the field's own surveys
(human-curated corpora), snowball 1-2 hops through OpenAlex citation
data, then filter by keyword relevance + in-corpus citation frequency.

Stages:
  1. seeds     — resolve seed surveys, fetch their referenced_works
  2. snowball  — batch-fetch candidates, tally in-corpus citations
  3. filter    — keyword score + in-corpus citation threshold
  4. export    — JSONL with schema v2 (includes real citation edges)

Checkpoints after every stage — safe to Ctrl+C and re-run.

Usage:
  python ingest_v2.py                       # full run (~3-6k papers)
  python ingest_v2.py --stats               # dry-run: corpus stats only
  python ingest_v2.py --mailto you@x.com    # OpenAlex polite pool (recommended)

Validated 2026-07-20: 50/50 recall on interp-targeted arXiv query,
2/60 false positives on generic "large language models" query
(both FPs genuinely interp-adjacent: representational + head-intervention).
"""
import argparse, json, time, sys
from pathlib import Path

import requests

OPENALEX = "https://api.openalex.org/works"
S2 = "https://api.semanticscholar.org/graph/v1"


def s2_survey_refs(arxiv_id, session, ckpt_dir=None):
    """Reference DOIs of a survey via Semantic Scholar.

    OpenAlex does not index reference lists of arXiv-only records (the seed
    surveys come back with referenced_works: 0), so the snowball seeds
    resolve through S2, which has full arXiv coverage. Without an API key
    (env S2_API_KEY) the shared pool 429s often — the per-survey cache in
    ckpt_dir makes retries cheap.
    """
    cache = ckpt_dir / f"s2_seed_{arxiv_id}.json" if ckpt_dir else None
    if cache and cache.exists():
        d = json.loads(cache.read_text())
        return d["title"], d["dois"]
    import os
    key = os.environ.get("S2_API_KEY")
    headers = {"x-api-key": key} if key else {}
    for attempt in range(10):
        r = session.get(f"{S2}/paper/arXiv:{arxiv_id}",
                        params={"fields": "title,references.externalIds"},
                        headers=headers, timeout=60)
        if r.status_code == 429:
            wait = min(2 ** attempt * 5, 120)
            print(f"  [s2 429] waiting {wait}s... (tip: S2_API_KEY env avoids this)")
            time.sleep(wait)
            continue
        r.raise_for_status()
        d = r.json()
        dois = []
        for ref in d.get("references") or []:
            ext = ref.get("externalIds") or {}
            if ext.get("DOI"):
                dois.append(ext["DOI"].lower())
            elif ext.get("ArXiv"):
                dois.append(f"10.48550/arxiv.{ext['ArXiv'].lower()}")
        if cache:
            cache.write_text(json.dumps({"title": d.get("title"), "dois": dois}))
        return d.get("title"), dois
    raise RuntimeError("Semantic Scholar unreachable after retries")

# --- Seed surveys: the field's own curated maps (arXiv IDs) ---
SEED_ARXIV_IDS = [
    "2404.14082",  # Bereska & Gavves — Mechanistic interpretability for AI safety: a review
    "2501.16496",  # Sharkey et al. — Open problems in mechanistic interpretability
    "2407.02646",  # Rai et al. — Practical review of MI for transformer LMs
]

# --- Relevance filter: title/abstract keywords (case-insensitive) ---
CORE_KEYWORDS = [
    "mechanistic interpretab", "sparse autoencoder", "superposition",
    "activation patching", "attribution patching", "circuit discovery",
    "transformer circuit", "interpretab", "probing", "probe",
    "feature visualization", "dictionary learning", "monosemantic",
    "polysemantic", "induction head", "in-context learning head",
    "residual stream", "activation steering", "representation engineering",
    "steering vector", "latent knowledge", "eliciting latent",
    "neuron interpretab", "logit lens", "tuned lens", "patchscopes",
    "causal tracing", "causal scrubbing", "path patching",
    "attention head", "sae ", "transcoder", "crosscoder",
    "linear representation", "toy models of superposition",
    "grokking", "knowledge editing", "model editing", "rome",
    "membership inference",  # borderline, kept scored low via single hit
]
# Keywords strong enough on their own to include a paper
STRONG_KEYWORDS = [
    "mechanistic interpretab", "sparse autoencoder", "superposition",
    "activation patching", "circuit", "induction head", "residual stream",
    "monosemantic", "transcoder", "crosscoder", "logit lens",
    "activation steering", "steering vector", "dictionary learning",
]

MIN_YEAR = 2015          # interp as a field starts ~2015 (feature viz); keeps landmark oldies via seeds
MIN_IN_CORPUS_CITES = 2  # cited by >=2 other corpus papers, OR strong keyword hit

FIELDS = ("id,doi,title,publication_year,cited_by_count,authorships,"
          "abstract_inverted_index,referenced_works,primary_location,ids")


def reconstruct_abstract(inv_index):
    if not inv_index:
        return ""
    pos = []
    for word, positions in inv_index.items():
        for p in positions:
            pos.append((p, word))
    pos.sort()
    return " ".join(w for _, w in pos)


def normalize_work(w):
    authors = [a["author"]["display_name"] for a in (w.get("authorships") or [])
               if a.get("author", {}).get("display_name")]
    venue = ((w.get("primary_location") or {}).get("source") or {}).get("display_name")
    arxiv_id = None
    loc = w.get("primary_location") or {}
    landing = loc.get("landing_page_url") or ""
    if "arxiv.org" in landing:
        arxiv_id = landing.rstrip("/").split("/")[-1]
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
        self.params = {}
        if mailto:
            self.params["mailto"] = mailto  # polite pool: higher rate limits

    def get(self, **params):
        params.update(self.params)
        for attempt in range(6):
            try:
                r = self.s.get(OPENALEX, params=params, timeout=60)
                if r.status_code == 429:
                    wait = min(2 ** attempt * 5, 120)
                    print(f"  [429] waiting {wait}s...")
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                return r.json()
            except requests.RequestException as e:
                print(f"  [net] {e}; retrying...")
                time.sleep(5)
        raise RuntimeError("OpenAlex unreachable after retries")

    def get_one(self, path):
        """Single-work lookup: GET /works/{doi-or-id}. 404 -> None."""
        for attempt in range(6):
            try:
                r = self.s.get(f"{OPENALEX}/{path}", params={**self.params, "select": FIELDS}, timeout=60)
                if r.status_code == 429:
                    wait = min(2 ** attempt * 5, 120)
                    print(f"  [429] waiting {wait}s...")
                    time.sleep(wait)
                    continue
                if r.status_code == 404:
                    return None
                r.raise_for_status()
                return r.json()
            except requests.RequestException as e:
                print(f"  [net] {e}; retrying...")
                time.sleep(5)
        raise RuntimeError("OpenAlex unreachable after retries")

    def batch_by_dois(self, dois):
        """Fetch up to 50 works per call by DOI (pipe-OR filter)."""
        out = []
        for i in range(0, len(dois), 50):
            chunk = dois[i:i + 50]
            data = self.get(filter="doi:" + "|".join(chunk),
                            per_page=50, select=FIELDS)
            out.extend(data.get("results", []))
            time.sleep(0.15)
        return out

    def batch_by_ids(self, openalex_ids):
        """Fetch up to 50 works per call by OpenAlex ID."""
        out = []
        for i in range(0, len(openalex_ids), 50):
            chunk = openalex_ids[i:i + 50]
            id_filter = "|".join(f"https://openalex.org/{c}" for c in chunk)
            data = self.get(filter=f"ids.openalex:{id_filter}",
                            per_page=50, select=FIELDS)
            out.extend(data.get("results", []))
            time.sleep(0.15)
        return out


def keyword_score(title, abstract):
    text = (title + " " + abstract).lower()
    hits = sum(1 for k in CORE_KEYWORDS if k in text)
    strong = any(k in text for k in STRONG_KEYWORDS)
    return hits, strong


def checkpoint(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))
    print(f"  [ckpt] {path} ({len(obj)} items)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/raw/interp_corpus.jsonl")
    ap.add_argument("--ckpt-dir", default="data/raw/.ckpt")
    ap.add_argument("--mailto", default=None)
    ap.add_argument("--stats", action="store_true", help="print stats, don't write corpus")
    ap.add_argument("--max-candidates", type=int, default=25000)
    args = ap.parse_args()

    oa = OpenAlex(args.mailto)
    ck = Path(args.ckpt_dir)

    # ---------- Stage 1: seeds ----------
    seed_path = ck / "seeds.json"
    if seed_path.exists():
        seed_refs = json.loads(seed_path.read_text())
        print(f"[1] seeds cached ({len(seed_refs)} referenced works)")
    else:
        print("[1] resolving seed surveys via Semantic Scholar...")
        s2 = requests.Session()
        seed_dois = set()
        for ax in SEED_ARXIV_IDS:
            title, dois = s2_survey_refs(ax, s2, ck)
            print(f"  seed: {(title or ax)[:70]} ({len(dois)} refs with DOI/arXiv)")
            seed_dois.update(dois)
            time.sleep(1)
        works = oa.batch_by_dois(sorted(seed_dois))
        print(f"  resolved {len(works)}/{len(seed_dois)} references in OpenAlex")
        seed_refs = sorted({w["id"].replace("https://openalex.org/", "") for w in works})
        checkpoint(seed_path, seed_refs)

    # ---------- Stage 2: snowball ----------
    cand_path = ck / "candidates.json"
    if cand_path.exists():
        works = json.loads(cand_path.read_text())
        print(f"[2] candidates cached ({len(works)})")
    else:
        print(f"[2] fetching {len(seed_refs)} seed references + expanding...")
        works_raw = oa.batch_by_ids(seed_refs[:args.max_candidates])
        works = [normalize_work(w) for w in works_raw]
        # second hop: references of the most-cited seed refs that look relevant
        hop2_seeds = set()
        for w in works:
            hits, strong = keyword_score(w["title"], w["abstract"])
            if strong and w["cited_by_count"] >= 10:
                hop2_seeds.update(w["referenced_works"][:30])  # cap per paper
        hop2_seeds = sorted(hop2_seeds - {w["id"] for w in works})[:args.max_candidates]
        print(f"  hop2: {len(hop2_seeds)} additional candidates")
        works2_raw = oa.batch_by_ids(hop2_seeds)
        works.extend(normalize_work(w) for w in works2_raw)
        # dedupe
        seen, deduped = set(), []
        for w in works:
            if w["id"] not in seen:
                seen.add(w["id"])
                deduped.append(w)
        works = deduped
        checkpoint(cand_path, works)

    # ---------- Stage 3: filter ----------
    print("[3] filtering...")
    ids_in_pool = {w["id"] for w in works}
    in_corpus_cites = {w["id"]: 0 for w in works}
    for w in works:
        for ref in w["referenced_works"]:
            if ref in in_corpus_cites:
                in_corpus_cites[ref] += 1

    corpus = []
    for w in works:
        if not w["abstract"] or not w["year"] or w["year"] < MIN_YEAR:
            continue
        hits, strong = keyword_score(w["title"], w["abstract"])
        w["_kw_hits"] = hits
        w["_in_corpus_cites"] = in_corpus_cites[w["id"]]
        if strong or hits >= 2 or w["_in_corpus_cites"] >= MIN_IN_CORPUS_CITES:
            corpus.append(w)

    corpus.sort(key=lambda w: -w["cited_by_count"])
    print(f"  corpus: {len(corpus)} papers (from {len(works)} candidates)")

    # stats
    from collections import Counter
    years = Counter(w["year"] for w in corpus)
    print("  years:", dict(sorted(years.items())))
    venues = Counter(w["venue"] or "?" for w in corpus).most_common(8)
    print("  top venues:", venues)
    corpus_id_set = {c["id"] for c in corpus}
    n_edges = sum(1 for w in corpus for r in w["referenced_works"] if r in corpus_id_set)
    print(f"  in-corpus citation edges: {n_edges}")

    if args.stats:
        return

    # ---------- Stage 4: export ----------
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for w in corpus:
            w["edges"] = [r for r in w["referenced_works"] if r in corpus_id_set]
            del w["referenced_works"]
            f.write(json.dumps(w) + "\n")
    print(f"[4] wrote {out} — {len(corpus)} papers")


if __name__ == "__main__":
    main()
