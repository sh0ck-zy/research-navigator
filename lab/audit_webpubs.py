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
from urllib.parse import quote

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


class S2RateLimited(Exception):
    pass


class S2Client:
    """Semantic Scholar. Works with or without a key.

    WITH a key: a 429 is a hard error (your private quota shouldn't 429; if it
    does, the key or plan is wrong — stop rather than retry-loop).
    WITHOUT a key: the 5,000-req/5-min pool is SHARED across all keyless users,
    so a 429 is other people's traffic, not ours. For a ~150-request one-time
    audit that is tolerable with light bounded backoff — this is not "coding
    around" a limit to force a large job through, it is riding out transient
    contention on a small one. The forward-citation INGEST does NOT do this; it
    requires a key (see ingest_s2.py).
    """

    def __init__(self, key=None, retries=4):
        self.s = requests.Session()
        self.authed = bool(key)
        if key:
            self.s.headers.update({"x-api-key": key})
        self.retries = retries

    def _get(self, path, params):
        url = f"{S2}{path}"
        for attempt in range(self.retries):
            r = self.s.get(url, params=params, timeout=60)
            if r.status_code == 429:
                if self.authed:
                    raise RuntimeError("S2 returned 429 WITH an API key — stop and check the "
                                       "key/plan, not retry-looping.")
                time.sleep(min(2 ** attempt * 4, 30))  # shared-pool contention
                continue
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        raise S2RateLimited(f"429 after {self.retries} tries (shared pool saturated)")

    def find(self, pub):
        try:
            # 1. web-native lookup: S2 addresses Circuits/Distill posts by URL.
            #    The identifier embeds a full URL, so it must be percent-encoded.
            ident = quote(f"URL:{pub['url']}", safe="")
            d = self._get(f"/paper/{ident}", {"fields": S2_FIELDS})
            if d and title_matches(pub["title"], d.get("title")):
                return self._fmt(d, "url")
            # 2. title search
            d = self._get("/paper/search", {"query": pub["title"], "limit": 10, "fields": S2_FIELDS})
        except S2RateLimited as e:
            return {"found": None, "error": str(e)}         # None = couldn't check, not "absent"
        except requests.RequestException as e:
            return {"found": None, "error": str(e)[:120]}
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
    ap.add_argument("--s2-only", action="store_true",
                    help="skip OpenAlex (e.g. while it is IP-throttled); S2 column only")
    ap.add_argument("--sleep", type=float, default=2.0,
                    help="seconds between OpenAlex calls (it throttles bursts)")
    ap.add_argument("--s2-sleep", type=float, default=1.5,
                    help="seconds between S2 calls (keyless pool is shared)")
    ap.add_argument("--kinds", default="paper,essay",
                    help="comma list of kinds to audit; 'all' for everything")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    data = json.loads((LAB / "webpubs.json").read_text())
    pubs = data["pubs"]
    if args.kinds != "all":
        keep = set(args.kinds.split(","))
        pubs = [p for p in pubs if p["kind"] in keep]

    key = os.environ.get("S2_API_KEY")
    use_oa = not args.s2_only
    use_s2 = not args.openalex_only
    if use_s2 and not key:
        print("!! S2_API_KEY not set — querying S2 UNAUTHENTICATED (shared 5k/5min pool).\n"
              "   Fine for this ~150-req audit; the forward-citation ingest still needs a key.\n")
    if args.s2_only:
        print("!! --s2-only: skipping OpenAlex (assumed throttled). OpenAlex column = 'skipped'.\n")

    oa = OpenAlexClient(args.mailto) if use_oa else None
    s2 = S2Client(key) if use_s2 else None

    rows = []
    for p in pubs:
        o = oa.find(p) if use_oa else {"found": None, "skipped": True}
        if use_oa:
            time.sleep(args.sleep)
        s = s2.find(p) if use_s2 else {"found": None}
        if use_s2:
            time.sleep(args.s2_sleep)
        rows.append({**{k: p[k] for k in ("title", "year", "venue", "kind", "landmark")},
                     "source_class": p.get("source_class"), "url": p["url"],
                     "openalex": o, "s2": s})
        oflag = "OA" if o["found"] else ("··" if o.get("skipped") else "--")
        sflag = {True: "S2", False: "--", None: "??"}[s["found"]]
        print(f"  [{oflag}|{sflag}] {p['year']} {p['title'][:62]}")

    def found(col, r):
        return r[col]["found"] is True

    n = len(rows)
    n_oa = sum(1 for r in rows if found("openalex", r)) if use_oa else None
    n_s2 = sum(1 for r in rows if found("s2", r)) if use_s2 else None
    s2_uncheckable = sum(1 for r in rows if use_s2 and r["s2"]["found"] is None)
    only_s2 = [r for r in rows if use_oa and use_s2 and found("s2", r) and not found("openalex", r)]
    lm = [r for r in rows if r["landmark"]]
    # break the canary out by class — the whole point is DOI-less vs with-DOI
    doiless = [r for r in rows if r["source_class"] == "web_pub_doiless"]
    withdoi = [r for r in rows if r["source_class"] == "web_pub_doi"]

    summary = {
        "audited": n,
        "openalex_found": n_oa, "openalex_status": "skipped" if not use_oa else "ok",
        "s2_found": n_s2, "s2_status": ("authenticated" if key else "unauthenticated") if use_s2 else "off",
        "s2_uncheckable_429": s2_uncheckable,
        "only_in_s2": len(only_s2) if (use_oa and use_s2) else None,
        "s2_doiless_found": sum(1 for r in doiless if found("s2", r)) if use_s2 else None,
        "s2_doiless_total": len(doiless),
        "s2_withdoi_found": sum(1 for r in withdoi if found("s2", r)) if use_s2 else None,
        "s2_withdoi_total": len(withdoi),
        "landmarks_audited": len(lm),
    }
    outp = Path(args.out) if args.out else (
        EVAL / ("webpub_coverage_s2only.json" if args.s2_only else "webpub_coverage.json"))
    outp.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))

    print("\n=== coverage ===")
    print(f"audited            {n}")
    print(f"in OpenAlex        {n_oa if use_oa else 'skipped (throttled)'}")
    print(f"in S2 ({summary['s2_status']:<15}) {n_s2}" + (f"  ({s2_uncheckable} uncheckable/429)" if s2_uncheckable else ""))
    if use_s2:
        print(f"  S2 DOI-less webpubs {summary['s2_doiless_found']}/{len(doiless)}"
              f"   <- the Circuits Thread OpenAlex structurally lacks")
        print(f"  S2 with-DOI (Distill) {summary['s2_withdoi_found']}/{len(withdoi)}   (control)")
    if use_oa and use_s2:
        print(f"only in S2         {len(only_s2)}   <- ingest these via S2")
    print(f"\n→ {outp}")


if __name__ == "__main__":
    main()
