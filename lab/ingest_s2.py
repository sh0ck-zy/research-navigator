"""lab/ingest_s2.py — supplemental citation-graph ingestion from Semantic Scholar.

OpenAlex is the primary source. S2 fills the hole OpenAlex structurally cannot:
web-native, DOI-less publications (the Transformer Circuits Thread), and the
forward-citation subtree hanging off them — which is where the SAE wave lives.

  1. seeds     every webpub the audit found in S2 but NOT in OpenAlex
  2. backward  those seeds' references
  3. forward   /paper/{id}/citations, paginated — the actual point of this file
  4. merge     into the existing OpenAlex candidate pool, deduping on
               arXiv id -> DOI -> normalized title. MERGE, never append: an
               existing OpenAlex record keeps its id and gains the S2 edges,
               and `sources` records every provider that contributed.

Every record and every edge carries source='openalex'|'s2' (the schema slot
CITES.source has been reserved for this since day one).

REQUIRES an API key. There is no unauthenticated fallback and no rate-limit
workaround by design:

    export S2_API_KEY=...

Usage:
  python lab/ingest_s2.py --coverage lab/eval/webpub_coverage.json \
      --pool data/raw/.ckpt_v3/candidates_clean.json \
      --out data/raw/.ckpt_v3/candidates_s2merged.json
"""
import argparse
import json
import os
import re
import time
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
EVAL = ROOT / "lab" / "eval"
S2 = "https://api.semanticscholar.org/graph/v1"
PAPER_FIELDS = ("paperId,externalIds,title,abstract,year,venue,citationCount,"
                "referenceCount,authors")


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def clean_arxiv(ax):
    if not ax:
        return None
    ax = re.sub(r"v\d+$", "", str(ax).strip())
    return ax if re.fullmatch(r"\d{4}\.\d{4,5}|[a-z-]+(\.[A-Z]{2})?/\d{7}", ax) else None


class S2:
    def __init__(self, key):
        if not key:
            raise SystemExit(
                "S2_API_KEY is not set.\n"
                "  export S2_API_KEY=...   (get a free key at "
                "https://www.semanticscholar.org/product/api)\n"
                "This script does not run unauthenticated.")
        self.s = requests.Session()
        self.s.headers.update({"x-api-key": key})

    def _get(self, path, params=None):
        r = self.s.get(f"{S2}{path}", params=params or {}, timeout=90)
        if r.status_code == 429:
            raise SystemExit("S2 returned 429 with an API key — stop and check the key "
                             "or your plan's limits. Not retry-looping around it.")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def paper(self, ident):
        return self._get(f"/paper/{ident}", {"fields": PAPER_FIELDS})

    def citations(self, pid, cap=10000, page=1000):
        """Forward citations — the SAE wave lives here."""
        out, offset = [], 0
        while offset < cap:
            d = self._get(f"/paper/{pid}/citations",
                          {"fields": PAPER_FIELDS, "limit": page, "offset": offset})
            if not d or not d.get("data"):
                break
            out += [x["citingPaper"] for x in d["data"] if x.get("citingPaper")]
            if d.get("next") is None:
                break
            offset = d["next"]
            time.sleep(0.1)
        return out

    def references(self, pid, cap=2000, page=1000):
        out, offset = [], 0
        while offset < cap:
            d = self._get(f"/paper/{pid}/references",
                          {"fields": PAPER_FIELDS, "limit": page, "offset": offset})
            if not d or not d.get("data"):
                break
            out += [x["citedPaper"] for x in d["data"] if x.get("citedPaper")]
            if d.get("next") is None:
                break
            offset = d["next"]
            time.sleep(0.1)
        return out


def normalize_s2(p):
    """S2 record -> the same shape ingest_v3.normalize() produces."""
    ex = p.get("externalIds") or {}
    return {
        "id": f"S2:{p['paperId']}",
        "arxiv_id": clean_arxiv(ex.get("ArXiv")),
        "doi": ex.get("DOI"),
        "title": p.get("title") or "Untitled",
        "authors": [a.get("name") for a in (p.get("authors") or []) if a.get("name")],
        "year": p.get("year"),
        "venue": p.get("venue") or None,
        "cited_by_count": p.get("citationCount") or 0,
        "abstract": p.get("abstract") or "",
        "referenced_works": [],
        "source": "s2",
    }


def merge_key(rec):
    """Dedupe precedence: arXiv id -> DOI -> normalized title."""
    if rec.get("arxiv_id"):
        return ("arxiv", rec["arxiv_id"])
    if rec.get("doi"):
        return ("doi", rec["doi"].lower())
    return ("title", norm(rec["title"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coverage", default=str(EVAL / "webpub_coverage.json"))
    ap.add_argument("--pool", default=str(ROOT / "data/raw/.ckpt_v3/candidates_clean.json"))
    ap.add_argument("--out", default=str(ROOT / "data/raw/.ckpt_v3/candidates_s2merged.json"))
    ap.add_argument("--ckpt", default=str(ROOT / "data/raw/.ckpt_s2"))
    ap.add_argument("--landmarks-only", action="store_true",
                    help="seed only from webpubs flagged landmark=true")
    args = ap.parse_args()

    cov = json.loads(Path(args.coverage).read_text())
    seeds_meta = [r for r in cov["rows"]
                  if r["s2"].get("found") and not r["openalex"].get("found")
                  and r["kind"] in ("paper", "essay")
                  and (r["landmark"] if args.landmarks_only else True)]
    if not seeds_meta:
        raise SystemExit("No S2-only seeds in the coverage audit. Run lab/audit_webpubs.py "
                         "with S2_API_KEY set first.")
    print(f"[s2] {len(seeds_meta)} S2-only seeds (in S2, absent from OpenAlex)")

    api = S2(os.environ.get("S2_API_KEY"))
    ck = Path(args.ckpt); ck.mkdir(parents=True, exist_ok=True)

    # ── 1-3 · seeds, references, forward citations ───────────────────────────
    fetched, edges = {}, []          # edges: (citing_id, cited_id, source)
    for meta in seeds_meta:
        pid = meta["s2"]["paperId"]
        cache = ck / f"{pid}.json"
        if cache.exists():
            blob = json.loads(cache.read_text())
        else:
            seed = api.paper(pid)
            refs = api.references(pid)
            cits = api.citations(pid)
            blob = {"seed": seed, "refs": refs, "cits": cits}
            cache.write_text(json.dumps(blob))
            print(f"  [s2] {meta['title'][:52]:<52} refs={len(refs)} citers={len(cits)}")
        s = normalize_s2(blob["seed"])
        s["is_webpub_seed"] = True
        fetched.setdefault(s["id"], s)
        for r in blob["refs"]:
            if not r.get("paperId"):
                continue
            n = normalize_s2(r); fetched.setdefault(n["id"], n)
            edges.append((s["id"], n["id"], "s2"))
        for c in blob["cits"]:
            if not c.get("paperId"):
                continue
            n = normalize_s2(c); fetched.setdefault(n["id"], n)
            edges.append((n["id"], s["id"], "s2"))
    print(f"[s2] fetched {len(fetched)} records, {len(edges)} s2 edges")

    # ── 4 · merge into the OpenAlex pool ─────────────────────────────────────
    pool = json.loads(Path(args.pool).read_text())
    for w in pool:
        w.setdefault("source", "openalex")
        w.setdefault("sources", ["openalex"])
    index = {}
    for w in pool:
        index[merge_key(w)] = w
        if w.get("arxiv_id"):
            index[("arxiv", w["arxiv_id"])] = w
        if w.get("doi"):
            index[("doi", w["doi"].lower())] = w

    remap, added, merged = {}, 0, 0
    for sid, rec in fetched.items():
        k = merge_key(rec)
        alt = [k]
        if rec.get("arxiv_id"):
            alt.append(("arxiv", rec["arxiv_id"]))
        if rec.get("doi"):
            alt.append(("doi", rec["doi"].lower()))
        alt.append(("title", norm(rec["title"])))
        hit = next((index[a] for a in alt if a in index), None)
        if hit:                                  # MERGE, never append
            remap[sid] = hit["id"]
            if "s2" not in hit["sources"]:
                hit["sources"].append("s2")
            if not hit.get("abstract") and rec.get("abstract"):
                hit["abstract"] = rec["abstract"]
            hit["cited_by_count"] = max(hit.get("cited_by_count") or 0,
                                        rec.get("cited_by_count") or 0)
            merged += 1
        else:
            rec["sources"] = ["s2"]
            pool.append(rec)
            for a in alt:
                index.setdefault(a, rec)
            remap[sid] = sid
            added += 1

    by_id = {w["id"]: w for w in pool}
    edge_src = {}
    n_edge = 0
    for a, b, src in edges:
        ca, cb = remap.get(a, a), remap.get(b, b)
        if ca == cb or ca not in by_id or cb not in by_id:
            continue
        w = by_id[ca]
        if cb not in w["referenced_works"]:
            w["referenced_works"].append(cb)
            n_edge += 1
        edge_src.setdefault(ca, {})[cb] = src
    for w in pool:
        if w["id"] in edge_src:
            w["_edge_source"] = {**w.get("_edge_source", {}), **edge_src[w["id"]]}

    Path(args.out).write_text(json.dumps(pool))
    audit = {"s2_only_seeds": len(seeds_meta), "s2_records_fetched": len(fetched),
             "merged_into_existing": merged, "added_new": added,
             "new_edges": n_edge, "pool_size": len(pool),
             "by_source": dict(Counter(s for w in pool for s in w.get("sources", ["openalex"])))}
    (EVAL / "s2_merge_audit.json").write_text(json.dumps(audit, indent=2))
    print(f"[s2] merged={merged} added={added} new_edges={n_edge} pool={len(pool)}")
    print(f"→ {args.out}\n→ {EVAL / 's2_merge_audit.json'}")


if __name__ == "__main__":
    main()
