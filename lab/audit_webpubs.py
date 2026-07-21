"""lab/audit_webpubs.py — coverage audit for DOI-less / web-native interp publications.

Resolves EVERY entry in lab/webpubs.json against BOTH sources, programmatically,
and reports which source has which. No assumptions: a pub counts as found only if
a returned record's title verifies against the expected title.

  OpenAlex — title search (no key needed)
  Semantic Scholar — /paper/search, plus a direct /paper/URL:<url> lookup, which
                     is how S2 addresses web-native publications like the
                     Circuits Thread.

S2 REQUIRES an API key in the environment:

    export S2_API_KEY=...

Without it this script reports the OpenAlex column and marks the S2 column
'NO_KEY' — it does not throttle, sleep-loop or otherwise work around the
unauthenticated rate limit.

Usage:
  python lab/audit_webpubs.py                 # both sources if the key is set
  python lab/audit_webpubs.py --openalex-only
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
LAB = Path(__file__).resolve().parent
EVAL = LAB / "eval"
OPENALEX = "https://api.openalex.org/works"
S2 = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS = "paperId,externalIds,title,year,venue,citationCount,referenceCount"


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def title_matches(expected, got):
    a, b = norm(expected), norm(got)
    if not a or not b:
        return False
    if a == b or a.startswith(b) or b.startswith(a):
        return True
    ta, tb = set(a.split()), set(b.split())
    return len(ta & tb) / max(1, len(ta | tb)) >= 0.6


class OpenAlexClient:
    def __init__(self, mailto=None):
        self.s = requests.Session()
        self.mailto = mailto

    SELECT = "id,doi,title,publication_year,cited_by_count,referenced_works,primary_location"

    def _query(self, filt):
        params = {"per_page": 10, "select": self.SELECT, "filter": filt}
        if self.mailto:
            params["mailto"] = self.mailto
        for attempt in range(8):
            r = self.s.get(OPENALEX, params=params, timeout=60)
            if r.status_code == 429:  # polite-pool backoff, same as ingest_v3
                time.sleep(min(2 ** attempt * 5, 120))
                continue
            r.raise_for_status()
            return r.json().get("results", [])
        raise RuntimeError("OpenAlex kept returning 429")

    def find(self, pub, year_tol=2):
        """Title search is not enough, in BOTH directions:
          • false negative — OpenAlex stores some records with corrupted titles
            (Toy Models of Superposition is filed as "Governance Architecture for
            Neural Network Superposition"), so we try the arXiv DOI first when the
            pub has one.
          • false positive — OpenAlex contains empty stub records that reuse a
            famous title under a later, unrelated arXiv id (a "Scaling
            Monosemanticity" stub dated 2026 with 0 citations and 0 references,
            versus the real 2024 Circuits publication). So a title hit must also
            agree on year.
        """
        try:
            if pub.get("arxiv_id"):
                res = self._query(f"doi:10.48550/arxiv.{pub['arxiv_id']}")
                if res:
                    return self._fmt(res[0], "arxiv_doi", corrupt_title=
                                     not title_matches(pub["title"], res[0].get("title")))
            q = re.sub(r"[^A-Za-z0-9 ]+", " ", pub["title"]).strip()
            res = self._query(f"title.search:{q}")
        except requests.RequestException as e:
            return {"found": False, "error": str(e)[:120]}

        cands = [w for w in res if title_matches(pub["title"], w.get("title"))]
        if not cands:
            return {"found": False}
        good = [w for w in cands
                if w.get("publication_year") and abs(w["publication_year"] - pub["year"]) <= year_tol]
        if not good:
            n = self._fmt(cands[0], "title_search")
            return {"found": False, "rejected_year_mismatch": True,
                    "near_miss": {k: n[k] for k in ("id", "doi", "title", "year",
                                                    "cited_by_count", "n_refs")}}
        return self._fmt(good[0], "title_search")

    @staticmethod
    def _fmt(hit, via, corrupt_title=False):
        return {"found": True, "via": via,
                "id": hit["id"].replace("https://openalex.org/", ""),
                "doi": (hit.get("doi") or "").replace("https://doi.org/", "") or None,
                "title": hit.get("title"), "year": hit.get("publication_year"),
                "cited_by_count": hit.get("cited_by_count"),
                "n_refs": len(hit.get("referenced_works") or []),
                "corrupt_title": corrupt_title}


class S2Client:
    """Semantic Scholar. Requires S2_API_KEY; no rate-limit workarounds."""

    def __init__(self, key):
        self.s = requests.Session()
        self.s.headers.update({"x-api-key": key})

    def _get(self, path, params):
        r = self.s.get(f"{S2}{path}", params=params, timeout=60)
        if r.status_code == 429:
            raise RuntimeError("S2 returned 429 even with an API key — stop and check the key/plan, "
                               "do not retry-loop.")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def find(self, pub):
        # 1. web-native lookup: S2 addresses Circuits/Distill posts by URL
        try:
            d = self._get(f"/paper/URL:{pub['url']}", {"fields": S2_FIELDS})
            if d and title_matches(pub["title"], d.get("title")):
                return self._fmt(d, "url")
        except requests.RequestException:
            d = None
        # 2. title search
        try:
            d = self._get("/paper/search", {"query": pub["title"], "limit": 10, "fields": S2_FIELDS})
        except requests.RequestException as e:
            return {"found": False, "error": str(e)[:120]}
        for c in (d or {}).get("data", []):
            if title_matches(pub["title"], c.get("title")):
                return self._fmt(c, "search")
        return {"found": False}

    @staticmethod
    def _fmt(d, via):
        ex = d.get("externalIds") or {}
        return {"found": True, "via": via, "paperId": d.get("paperId"),
                "doi": ex.get("DOI"), "arxiv_id": ex.get("ArXiv"),
                "title": d.get("title"), "year": d.get("year"),
                "citationCount": d.get("citationCount"),
                "referenceCount": d.get("referenceCount")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mailto", default=None)
    ap.add_argument("--openalex-only", action="store_true")
    ap.add_argument("--sleep", type=float, default=2.0,
                    help="seconds between OpenAlex calls (it throttles bursts)")
    ap.add_argument("--kinds", default="paper,essay",
                    help="comma list of kinds to audit; 'all' for everything")
    args = ap.parse_args()

    data = json.loads((LAB / "webpubs.json").read_text())
    pubs = data["pubs"]
    if args.kinds != "all":
        keep = set(args.kinds.split(","))
        pubs = [p for p in pubs if p["kind"] in keep]

    key = os.environ.get("S2_API_KEY")
    use_s2 = bool(key) and not args.openalex_only
    if not args.openalex_only and not key:
        print("!! S2_API_KEY not set — S2 column will report NO_KEY.\n"
              "   export S2_API_KEY=... and re-run to complete the audit.\n")

    oa = OpenAlexClient(args.mailto)
    s2 = S2Client(key) if use_s2 else None

    rows = []
    for p in pubs:
        o = oa.find(p)
        time.sleep(args.sleep)
        if use_s2:
            s = s2.find(p)
            time.sleep(0.15)
        else:
            s = {"found": None}
        rows.append({**{k: p[k] for k in ("title", "year", "venue", "kind", "landmark")},
                     "url": p["url"], "openalex": o, "s2": s})
        oflag = "OA" if o["found"] else "--"
        sflag = ("S2" if s["found"] else "--") if s["found"] is not None else "??"
        print(f"  [{oflag}|{sflag}] {p['year']} {p['title'][:64]}")

    n = len(rows)
    n_oa = sum(1 for r in rows if r["openalex"]["found"])
    n_s2 = sum(1 for r in rows if r["s2"]["found"]) if use_s2 else None
    only_s2 = [r for r in rows if use_s2 and r["s2"]["found"] and not r["openalex"]["found"]]
    neither = [r for r in rows if not r["openalex"]["found"] and (r["s2"]["found"] is False)]
    lm = [r for r in rows if r["landmark"]]

    summary = {
        "audited": n, "openalex_found": n_oa,
        "s2_found": n_s2, "s2_status": "ok" if use_s2 else "NO_KEY",
        "only_in_s2": len(only_s2) if use_s2 else None,
        "in_neither": len(neither) if use_s2 else None,
        "landmarks_audited": len(lm),
        "landmarks_in_openalex": sum(1 for r in lm if r["openalex"]["found"]),
        "landmarks_in_s2": (sum(1 for r in lm if r["s2"]["found"]) if use_s2 else None),
    }
    (EVAL / "webpub_coverage.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=2))

    print(f"\n=== coverage ===")
    print(f"audited            {n}")
    print(f"in OpenAlex        {n_oa}  ({100*n_oa/n:.0f}%)")
    print(f"in Semantic Schol. {n_s2 if use_s2 else 'NO_KEY — set S2_API_KEY'}")
    if use_s2:
        print(f"only in S2         {len(only_s2)}   <- these are the ones to ingest via S2")
        print(f"in neither         {len(neither)}")
    print(f"landmark canaries  {summary['landmarks_in_openalex']}/{len(lm)} in OpenAlex")
    print(f"\n→ {EVAL / 'webpub_coverage.json'}")


if __name__ == "__main__":
    main()
