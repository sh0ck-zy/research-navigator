"""lab/latex_refs/fetch_sources.py — Stage 1: fetch arXiv e-print LaTeX source.

Consumes the resolved universe from Stage 0 (status local|searched, each with an
arXiv id) and downloads the e-print package for each, paced >=3s. arXiv returns
one of three things, which we classify by magic bytes:

  tar/tar.gz  -> the LaTeX source; extract .tex/.bbl/.bib into sources/<Wid>/
  single .gz  -> a one-file submission; write as main.tex
  %PDF        -> pdf_only: the author submitted a PDF, no TeX exists (an
                 EXPECTED, legitimate miss — counts against the 85% denominator
                 but is not an error)

Papers that are unresolved / no_arxiv_id in Stage 0 are recorded status=skipped
and never hit the network. The only egress is arXiv e-print, one GET per paper.

Usage:
  python -m lab.latex_refs.fetch_sources               # full run (resumable)
  python -m lab.latex_refs.fetch_sources --limit 10    # smoke test
"""
import argparse
import gzip
import io
import json
import sys
import tarfile
import time
from collections import Counter
from urllib.request import Request, urlopen

from .common import (LATEX, SOURCES, aggregate, load_ckpt, oa_key, pct,
                     print_status_by_cluster, save_ckpt)

STAGE = "fetch"
EPRINT = "https://export.arxiv.org/e-print/"
UA = "clarity-research/latex_refs (mailto:sh0ck.zy.25@gmail.com)"
PACE = 3.0
KEEP_EXT = (".tex", ".bbl", ".bib")
MAX_FILE = 8 * 1024 * 1024   # skip any single member larger than 8 MB (figures/data)


def _safe_members(tf):
    """Yield (relpath, bytes) for regular files we care about, rejecting path
    traversal and oversized blobs."""
    for m in tf.getmembers():
        if not m.isfile():
            continue
        name = m.name.lstrip("./")
        if name.startswith("/") or ".." in name.split("/"):
            continue
        if not name.lower().endswith(KEEP_EXT):
            continue
        if m.size > MAX_FILE:
            continue
        try:
            data = tf.extractfile(m).read()
        except Exception:  # noqa: BLE001
            continue
        yield name, data


def _write(wid, files):
    """Write {relpath: bytes} under sources/<Wid>/, return manifest list."""
    root = SOURCES / wid
    root.mkdir(parents=True, exist_ok=True)
    manifest = []
    for rel, data in files.items():
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        manifest.append({"file": rel, "bytes": len(data)})
    return manifest


def classify_and_extract(wid, raw):
    """Return (status, manifest). status in fetched|pdf_only|empty."""
    if raw[:5] == b"%PDF-":
        return "pdf_only", []
    files = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:*") as tf:
            for rel, data in _safe_members(tf):
                files[rel] = data
    except tarfile.ReadError:
        # Not a tar: a single-file submission, possibly gzipped.
        try:
            dec = gzip.decompress(raw)
        except (OSError, EOFError):
            dec = raw
        if dec[:5] == b"%PDF-":
            return "pdf_only", []
        files["main.tex"] = dec
    if not files:
        return "empty", []
    return "fetched", _write(wid, files)


def fetch_one(arxiv_id, retries=3):
    url = EPRINT + arxiv_id
    last = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": UA})
            with urlopen(req, timeout=120) as r:
                return r.read()
        except Exception as ex:  # noqa: BLE001
            last = ex
            time.sleep(PACE * (attempt + 1))
    raise last


def process(idrec):
    wid = idrec["openalex_id"]
    ax = idrec.get("arxiv_id")
    base = {"openalex_id": wid, "arxiv_id": ax, "id_status": idrec["status"]}
    if idrec["status"] not in ("local", "searched") or not ax:
        return {**base, "status": "skipped", "files": [], "n_tex": 0, "n_bbl": 0, "n_bib": 0}
    time.sleep(PACE)
    try:
        raw = fetch_one(ax)
    except Exception as ex:  # noqa: BLE001
        return {**base, "status": "http_error", "files": [], "error": str(ex)[:200],
                "n_tex": 0, "n_bbl": 0, "n_bib": 0}
    status, manifest = classify_and_extract(wid, raw)
    n = lambda ext: sum(1 for m in manifest if m["file"].lower().endswith(ext))  # noqa: E731
    return {**base, "status": status, "bytes": len(raw), "files": manifest,
            "n_tex": n(".tex"), "n_bbl": n(".bbl"), "n_bib": n(".bib")}


def load_ids():
    """Resolved-universe records from Stage 0, in corpus order."""
    p = LATEX / "ids.jsonl"
    if not p.exists():
        sys.exit("Stage 0 output missing: run resolve_ids first (data/latex/ids.jsonl).")
    return [json.loads(l) for l in p.open() if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    ids = load_ids()
    attempt = [r for r in ids if r["status"] in ("local", "searched") and r.get("arxiv_id")]
    if args.limit:
        attempt = attempt[: args.limit]
    total = len(attempt)

    for i, idrec in enumerate(attempt, 1):
        wid = idrec["openalex_id"]
        if not args.force and load_ckpt(STAGE, wid):
            continue
        res = process(idrec)
        save_ckpt(STAGE, wid, res)
        print(f"[{i}/{total}] {wid} {idrec['arxiv_id']} {res['status']} "
              f"tex={res['n_tex']} bbl={res['n_bbl']} bib={res['n_bib']}", flush=True)

    write_reports(len(ids))


def write_reports(n_universe):
    recs = aggregate(STAGE, "fetch.jsonl")
    counts = Counter(r["status"] for r in recs)
    attempted = sum(counts[s] for s in ("fetched", "pdf_only", "http_error", "empty"))
    fetched = counts["fetched"]
    print("\n=== Stage 1: e-print fetch ===")
    for s in ("fetched", "pdf_only", "http_error", "empty", "skipped"):
        if counts.get(s):
            print(f"  {s:11s} {counts[s]}")
    print(f"  FETCH RATE   {pct(fetched, attempted)}  (source-fetched of arXiv-attempted)")
    print(f"  gate: >=85% of resolved ids fetched, rest legitimately pdf_only")
    # Carry the Stage-0 no_arxiv_id miss, cross-tabbed by cluster: is the third
    # of the corpus that never resolved concentrated (journal/bioRxiv) or spread?
    ids_p = LATEX / "ids.jsonl"
    if ids_p.exists():
        idrecs = [json.loads(l) for l in ids_p.open() if l.strip()]
        print_status_by_cluster(idrecs, "openalex_id", "status", "no_arxiv_id",
                                "no_arxiv_id by cluster (unresolved third — concentrated = expected):")


if __name__ == "__main__":
    sys.exit(main())
