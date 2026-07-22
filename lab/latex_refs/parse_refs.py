"""lab/latex_refs/parse_refs.py — Stage 2: parse references from arXiv source.

For each paper fetched in Stage 1, locate its bibliography and split it into
individual reference entries. Three source shapes, tried in order:

  .bbl                 a compiled thebibliography (the reliable case — arXiv
                       requires it for the paper to build)
  .tex (inline)        \\begin{thebibliography}..\\end{thebibliography} embedded
                       in a main .tex when no separate .bbl was shipped
  .bib                 raw BibTeX @entries (rare in e-print, best-effort)

Each entry yields the structured signals the later stages need — and, crucially,
the ones NO aggregator captures: arXiv ids sitting in \\bibitem text and informal
web-pub URLs (transformer-circuits.pub, distill.pub, ...). Per entry:

  key        the LaTeX cite key ({...})
  title      best-effort title (first \\newblock after the author line)
  year       4-digit year from the (YYYY) label or the venue line
  arxiv_ids  arXiv ids in the entry (arXiv:XXXX, arxiv.org/abs/XXXX, \\eprint)
  doi        a DOI if present
  urls       every URL, each tagged with a webpub host label when one matches
  raw        the delatex'd entry text, trimmed (for Stage 3 title-matching/audit)

NO resolution to the corpus here (Stage 3) and NO in-text context extraction
(Stage 4). Reads the Stage-1 fetch checkpoints (so it runs incrementally while
the fetch is still going), writes one ckpt per paper, folds to refs.jsonl.

Usage:
  python -m lab.latex_refs.parse_refs                # all fetched papers (resumable)
  python -m lab.latex_refs.parse_refs --limit 15     # smoke test
  python -m lab.latex_refs.parse_refs --force        # re-parse everything
"""
import argparse
import glob
import json
import re
import sys
from collections import Counter

from .common import (CKPT, LATEX, SOURCES, WEBPUB_HOSTS, aggregate, clean_arxiv,
                     delatex, load_ckpt, pct, print_status_by_cluster, save_ckpt)

STAGE = "refs"

# arXiv id as it appears inside a reference: an explicit arXiv:/arxiv.org/abs/
# prefix, or a bare /abs/ path. We do NOT scrape bare 4.5-digit numbers — too
# many page ranges / years would masquerade as ids.
ARXIV_REF = re.compile(
    r"(?:arxiv\s*[:/]?\s*|arxiv\.org/(?:abs|pdf)/|/abs/|eprint\s*=?\s*[{\s])"
    r"(\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})",
    re.I,
)
URLCMD_RE = re.compile(r"\\url\{([^}]*)\}|\\href\{([^}]*)\}")
URL_RE = re.compile(r"https?://[^\s{}\\\"',]+")
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s{}\"',]+", re.I)
YEAR_RE = re.compile(r"\b(19[7-9]\d|20[0-4]\d)\b")
LABEL_YEAR_RE = re.compile(r"\((\d{4})[a-z]?\)")  # natbib label: (2016) / (2016b)
BIBITEM_HEAD = re.compile(r"^\s*(?:\[(?P<label>(?:[^\[\]]|\[[^\]]*\])*)\])?\s*\{(?P<key>[^}]*)\}", re.S)


def _strip_trailing_url(u):
    """URLs at a sentence end often swallow a trailing period/paren/brace."""
    return u.rstrip(".,;)}]")


def extract_urls(raw):
    """All URLs in the entry (from \\url{}, \\href{}, and bare http(s)), each
    tagged with a webpub host label when one of the tracked hosts matches."""
    found = []
    for m in URLCMD_RE.finditer(raw):
        found.append(m.group(1) or m.group(2) or "")
    found += URL_RE.findall(raw)
    out, seen = [], set()
    for u in found:
        u = _strip_trailing_url(u.strip())
        if not u or u in seen:
            continue
        seen.add(u)
        host = next((label for label, rx in WEBPUB_HOSTS if rx.search(u)), None)
        out.append({"url": u, "webpub": host})
    return out


def extract_arxiv_ids(raw):
    ids = []
    for m in ARXIV_REF.finditer(raw):
        c = clean_arxiv(m.group(1))
        if c and c not in ids:
            ids.append(c)
    return ids


def parse_entry(chunk):
    """Turn one post-\\bibitem chunk into a structured reference dict."""
    head = BIBITEM_HEAD.match(chunk)
    key, label = "", ""
    body = chunk
    if head:
        key = (head.group("key") or "").strip()
        label = (head.group("label") or "").strip()
        body = chunk[head.end():]

    # Title heuristic: natbib/plainnat put authors on the first line, then the
    # title in the first \newblock. Fall back to the whole (delatex'd) body.
    blocks = re.split(r"\\newblock", body)
    if len(blocks) >= 2:
        title = delatex(blocks[1]).rstrip(". ").strip()
    else:
        title = ""

    raw_clean = delatex(body)
    ly = LABEL_YEAR_RE.search(label)
    years = YEAR_RE.findall(body)
    year = int(ly.group(1)) if ly else (int(years[-1]) if years else None)

    dois = DOI_RE.findall(body)
    return {
        "key": key,
        "title": title,
        "year": year,
        "arxiv_ids": extract_arxiv_ids(body),
        "doi": _strip_trailing_url(dois[0]) if dois else None,
        "urls": extract_urls(body),
        "raw": raw_clean[:600],
    }


def split_thebib(text):
    """Return the list of \\bibitem chunks inside a thebibliography block.
    Accepts either a full .bbl or a .tex containing the environment."""
    m = re.search(r"\\begin\{thebibliography\}(.*?)\\end\{thebibliography\}", text, re.S)
    inner = m.group(1) if m else (text if "\\bibitem" in text else "")
    if "\\bibitem" not in inner:
        return []
    chunks = re.split(r"\\bibitem", inner)[1:]  # drop preamble before first \bibitem
    return [c for c in chunks if c.strip()]


BIB_FIELD = re.compile(r"(\w+)\s*=\s*(?:\{(.*?)\}|\"(.*?)\"|([^,}\n]+))", re.S)
BIB_ENTRY = re.compile(r"@\s*(\w+)\s*\{\s*([^,]*),(.*?)\n\s*\}\s*(?=@|\Z)", re.S)

# biblatex/biber .bbl: entries are \entry{key}{type}{opts} .. \endentry, with
# \field{name}{value}. A different beast from \bibitem — handled separately so
# newer papers (where the web-pub layer concentrates) don't silently drop refs.
BIBLATEX_ENTRY = re.compile(r"\\entry\{([^}]*)\}\{[^}]*\}\{")
BIBLATEX_FIELD = re.compile(r"\\field\{(\w+)\}\{")


def _braced(s, open_idx):
    """Content of the balanced {...} whose opening brace is at s[open_idx]."""
    depth = 0
    for i in range(open_idx, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[open_idx + 1:i]
    return s[open_idx + 1:]


def parse_biblatex(text):
    """Parse a biblatex .bbl (\\entry ... \\endentry with \\field{}{})."""
    refs = []
    for m in BIBLATEX_ENTRY.finditer(text):
        key = m.group(1).strip()
        end = text.find("\\endentry", m.end())
        body = text[m.end():end] if end != -1 else text[m.end():m.end() + 6000]
        fields = {}
        for fm in BIBLATEX_FIELD.finditer(body):
            fields.setdefault(fm.group(1), _braced(body, fm.end() - 1))
        eprint = fields.get("eprint", "")
        blob = body + (" arxiv:" + eprint if eprint else "")
        ym = YEAR_RE.search(fields.get("year") or fields.get("date") or "")
        refs.append({
            "key": key,
            "title": delatex(fields.get("title", "")).rstrip(". ").strip(),
            "year": int(ym.group(1)) if ym else None,
            "arxiv_ids": extract_arxiv_ids(blob),
            "doi": (fields.get("doi") or None),
            "urls": extract_urls(body),
            "raw": delatex(fields.get("title", "") + " — "
                           + (fields.get("journaltitle") or fields.get("booktitle") or ""))[:600],
        })
    return refs


def parse_bibtex(text):
    """Best-effort BibTeX parser for the rare .bib-only submission."""
    refs = []
    for m in BIB_ENTRY.finditer(text):
        etype, key, fields = m.group(1).lower(), m.group(2).strip(), m.group(3)
        if etype in ("comment", "string", "preamble"):
            continue
        fv = {}
        for fm in BIB_FIELD.finditer(fields):
            fv[fm.group(1).lower()] = delatex(next(g for g in fm.groups()[1:] if g is not None))
        blob = fields
        eprint = fv.get("eprint") or ""
        arxiv_ids = extract_arxiv_ids(blob + " arxiv:" + eprint if eprint else blob)
        yr = fv.get("year", "")
        ym = YEAR_RE.search(yr)
        refs.append({
            "key": key,
            "title": fv.get("title", "").rstrip(". ").strip(),
            "year": int(ym.group(1)) if ym else None,
            "arxiv_ids": arxiv_ids,
            "doi": fv.get("doi") or None,
            "urls": extract_urls(blob),
            "raw": (fv.get("title", "") + " — " + fv.get("journal", fv.get("booktitle", "")))[:600],
        })
    return refs


def read_sources(wid, manifest):
    """Yield (kind, text) for a paper's source files, .bbl first then .tex/.bib."""
    order = {".bbl": 0, ".tex": 1, ".bib": 2}
    files = sorted(manifest, key=lambda f: order.get(f["file"][f["file"].rfind("."):].lower(), 9))
    for f in files:
        p = SOURCES / wid / f["file"]
        if not p.exists():
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        ext = f["file"][f["file"].rfind("."):].lower()
        yield ext, txt


def process(fetchrec):
    wid = fetchrec["openalex_id"]
    base = {"openalex_id": wid, "arxiv_id": fetchrec.get("arxiv_id")}
    if fetchrec.get("status") != "fetched":
        return {**base, "source": "none", "reason": fetchrec.get("status"), "n_refs": 0, "refs": []}

    manifest = fetchrec.get("files") or []
    # 1) a .bbl or an inline thebibliography in any .tex
    for ext, txt in read_sources(wid, manifest):
        if ext in (".bbl", ".tex"):
            chunks = split_thebib(txt)
            if chunks:
                refs = [parse_entry(c) for c in chunks]
                return {**base, "source": "bbl" if ext == ".bbl" else "tex-inline",
                        "n_refs": len(refs), "refs": refs}
            if "\\entry{" in txt:  # biblatex/biber .bbl — \entry not \bibitem
                refs = parse_biblatex(txt)
                if refs:
                    return {**base, "source": "biblatex", "n_refs": len(refs), "refs": refs}
    # 2) fall back to raw BibTeX
    for ext, txt in read_sources(wid, manifest):
        if ext == ".bib":
            refs = parse_bibtex(txt)
            if refs:
                return {**base, "source": "bib", "n_refs": len(refs), "refs": refs}
    # 3) a .tex that just \includepdf's the real PDF body — no TeX bibliography
    #    exists to parse. An EXPECTED miss (like Stage-1 pdf_only), kept distinct
    #    from a genuine parse failure so the extract denominator stays honest.
    for ext, txt in read_sources(wid, manifest):
        if ext == ".tex" and "\\includepdf" in txt:
            return {**base, "source": "pdf_wrapper", "n_refs": 0, "refs": []}
    return {**base, "source": "no_bib", "n_refs": 0, "refs": []}


def load_fetched():
    """Every Stage-1 fetch checkpoint (read directly so Stage 2 can run while the
    fetch is still in flight), in stable id order."""
    recs = []
    for p in sorted(glob.glob(str(CKPT / "fetch" / "*.json"))):
        try:
            recs.append(json.loads(open(p).read()))
        except json.JSONDecodeError:
            continue
    if not recs:
        sys.exit("No Stage-1 fetch checkpoints found: run fetch_sources first.")
    return recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    fetched = [r for r in load_fetched() if r.get("status") == "fetched"]
    if args.limit:
        fetched = fetched[: args.limit]
    total = len(fetched)

    for i, fr in enumerate(fetched, 1):
        wid = fr["openalex_id"]
        if not args.force and load_ckpt(STAGE, wid):
            continue
        res = process(fr)
        save_ckpt(STAGE, wid, res)
        n_ax = sum(len(r["arxiv_ids"]) for r in res["refs"])
        n_web = sum(1 for r in res["refs"] for u in r["urls"] if u["webpub"])
        print(f"[{i}/{total}] {wid} {res['source']:10s} refs={res['n_refs']:3d} "
              f"arxiv={n_ax:3d} webpub={n_web}", flush=True)

    write_reports()


def write_reports():
    recs = aggregate(STAGE, "refs.jsonl")
    n = len(recs)
    with_refs = sum(1 for r in recs if r["n_refs"] > 0)
    by_source = Counter(r["source"] for r in recs)
    total_refs = sum(r["n_refs"] for r in recs)
    total_arxiv = sum(len(ref["arxiv_ids"]) for r in recs for ref in r["refs"])
    webpub = Counter(u["webpub"] for r in recs for ref in r["refs"]
                     for u in ref["urls"] if u["webpub"])

    # pdf_wrapper = a .tex that only \includepdf's a PDF body: no TeX bib exists,
    # an expected miss. Reported against the parseable universe so the extract
    # gate isn't unfairly dinged, AND against all fetched — both denominators.
    expected_miss = by_source.get("pdf_wrapper", 0)
    parseable = n - expected_miss

    print("\n=== Stage 2: reference parse ===")
    print(f"  papers parsed        {n}")
    for s, c in by_source.most_common():
        note = "  (expected miss: PDF body, no TeX bib)" if s == "pdf_wrapper" else ""
        print(f"    source={s:12s} {c}{note}")
    print(f"  EXTRACT RATE         {pct(with_refs, parseable)} of parseable "
          f"({pct(with_refs, n)} of all fetched)")
    print(f"  gate: >=90% of source-fetched papers with >=1 reference")
    print(f"  total references     {total_refs}")
    print(f"  arXiv ids in refs    {total_arxiv}")
    if webpub:
        print("  web-pub citations (the layer no aggregator captures):")
        for host, c in webpub.most_common():
            print(f"    {host:22s} {c}")
    else:
        print("  web-pub citations    0 so far (SAE-wave papers may still be fetching)")
    ids_p = LATEX / "ids.jsonl"
    if ids_p.exists():
        idrecs = [json.loads(l) for l in ids_p.open() if l.strip()]
        print_status_by_cluster(idrecs, "openalex_id", "status", "no_arxiv_id",
                                "no_arxiv_id by cluster (unresolved third — concentrated = expected):")


if __name__ == "__main__":
    sys.exit(main())
