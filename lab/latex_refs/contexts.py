"""lab/latex_refs/contexts.py — Stage 4: citation contexts from the .tex body.

For every \\cite-family command in a paper's TeX source, record WHERE and HOW the
citation happens:

  key       one row per (cite occurrence x key) — a \\citep{a,b} yields two rows
  cmd       the cite command verbatim, e.g. \\citep[e.g.][]{elhage2021framework}
  sentence  the enclosing sentence, verbatim TeX (whitespace-collapsed, capped),
            bounded by sentence punctuation with an abbreviation guard
            (et al. / e.g. / Fig. ... do not end a sentence)
  section   the delatex'd title of the nearest preceding \\(sub)section/chapter
            in the same file (null when none precedes, e.g. abstract)
  file      which source file the occurrence sits in

Comments are stripped before scanning; inline thebibliography blocks are
removed so \\bibitem text never masquerades as citing prose. No resolution
here — Stage 3 owns key->corpus mapping; joining contexts to edges is a
downstream concern. All local, no network. One ckpt per paper, folds to
data/latex/contexts.jsonl.

Usage:
  python -m lab.latex_refs.contexts                # full run (resumable)
  python -m lab.latex_refs.contexts --limit 15     # smoke test
"""
import argparse
import json
import re
import sys
from collections import Counter

from .common import LATEX, SOURCES, aggregate, delatex, load_ckpt, pct, save_ckpt
from .parse_refs import _braced

STAGE = "contexts"

CITE_RE = re.compile(r"\\([A-Za-z]*cite[A-Za-z]*)\*?\s*(?:\[[^\]]*\]\s*){0,2}\{([^{}]*)\}")
SECTION_RE = re.compile(r"\\(?:chapter|section|subsection|subsubsection)\*?\s*\{")
COMMENT_RE = re.compile(r"(?<!\\)%.*")
THEBIB_RE = re.compile(r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}", re.S)
BLANK_RE = re.compile(r"\n\s*\n")
# A '.', '!' or '?' ends a sentence only when NOT preceded by an abbreviation.
ABBREV = re.compile(r"(?:\bet al|\be\.g|\bi\.e|\bcf|\bvs|\bfig|\beq|\bsec|\bresp"
                    r"|\betc|\bpp|\bvol|\bno|\bca|\bal)\.$", re.I)
SENT_CAP = 350   # chars kept on each side of the cite command


def _is_boundary(text, i):
    """True if text[i] in .!? genuinely ends a sentence (abbrev-guarded)."""
    if text[i] not in ".!?":
        return False
    if i + 1 < len(text) and not text[i + 1].isspace():
        return False                      # e.g. '3.14', 'v1.2', file.tex
    return not ABBREV.search(text[max(0, i - 12):i + 1])


def sentence_around(text, s, e):
    """The sentence enclosing text[s:e]: scan back/forward to the nearest real
    sentence boundary or blank line, capped. Verbatim TeX, whitespace-collapsed."""
    lo = max(0, s - SENT_CAP)
    start = lo
    for i in range(s - 1, lo - 1, -1):
        if _is_boundary(text, i):
            start = i + 1
            break
        if text[i] == "\n" and i > 0 and BLANK_RE.match(text, i - 1):
            start = i
            break
    hi = min(len(text), e + SENT_CAP)
    end = hi
    for i in range(e, hi):
        if _is_boundary(text, i):
            end = i + 1
            break
        m = BLANK_RE.match(text, i)
        if m:
            end = i
            break
    return re.sub(r"\s+", " ", text[start:end]).strip()


def sections_in(text):
    """[(pos, delatex'd title)] for every sectioning command, in order."""
    out = []
    for m in SECTION_RE.finditer(text):
        title = _braced(text, m.end() - 1)
        out.append((m.start(), delatex(title)))
    return out


def contexts_in_file(fname, text):
    text = THEBIB_RE.sub(" ", COMMENT_RE.sub("", text))
    secs = sections_in(text)
    rows = []
    for m in CITE_RE.finditer(text):
        cmd_name, keys = m.group(1), m.group(2)
        if cmd_name in ("citestyle", "citename"):   # styling, not citations
            continue
        section = None
        for pos, title in secs:
            if pos < m.start():
                section = title
            else:
                break
        sent = sentence_around(text, m.start(), m.end())
        for key in (k.strip() for k in keys.split(",")):
            if key:
                rows.append({"key": key, "cmd": m.group(0), "file": fname,
                             "section": section or None, "sentence": sent})
    return rows


def process(paper):
    """paper is a refs.jsonl row (Stage 2): needs openalex_id + refs keys."""
    wid = paper["openalex_id"]
    ref_keys = {r["key"] for r in paper.get("refs") or [] if r.get("key")}
    rows = []
    root = SOURCES / wid
    if root.exists():
        for p in sorted(root.rglob("*.tex")):
            try:
                txt = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            rows.extend(contexts_in_file(str(p.relative_to(root)), txt))
    cited_keys = {r["key"] for r in rows}
    return {"openalex_id": wid, "n_contexts": len(rows),
            "n_cited_keys": len(cited_keys),
            "n_keys_in_refs": len(cited_keys & ref_keys),
            "contexts": rows}


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

    for i, paper in enumerate(papers, 1):
        wid = paper["openalex_id"]
        if not args.force and load_ckpt(STAGE, wid):
            continue
        res = process(paper)
        save_ckpt(STAGE, wid, res)
        print(f"[{i}/{total}] {wid} contexts={res['n_contexts']} "
              f"keys_in_refs={res['n_keys_in_refs']}/{res['n_cited_keys']}", flush=True)

    write_reports()


def write_reports():
    recs = aggregate(STAGE, "contexts.jsonl")
    n = len(recs)
    with_ctx = sum(1 for r in recs if r["n_contexts"] > 0)
    total_ctx = sum(r["n_contexts"] for r in recs)
    cited = sum(r["n_cited_keys"] for r in recs)
    joined = sum(r["n_keys_in_refs"] for r in recs)
    print("\n=== Stage 4: citation contexts ===")
    print(f"  papers scanned       {n}")
    print(f"  with >=1 context     {pct(with_ctx, n)}")
    print(f"  cite occurrences     {total_ctx}  (rows: one per occurrence x key)")
    print(f"  key join to Stage 2  {pct(joined, cited)}  (cited keys found in parsed refs)")


if __name__ == "__main__":
    sys.exit(main())
