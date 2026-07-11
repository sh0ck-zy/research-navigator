"""Parse Zotero-style .bib / .ris exports into paper dicts.

We lean on bibtexparser (pinned 1.4.x) and rispy rather than hand-rolling —
brace/escape handling and RIS tag variants are exactly where real exports
break naive parsers. Output rows carry whatever the file had; OpenAlex
enrichment fills the gaps later.
"""
import bibtexparser
import rispy

from backend.services.openalex import normalize_doi


def _clean(s: str | None) -> str | None:
    if not s:
        return None
    # BibTeX values often keep stray braces; RIS keeps line noise.
    return s.replace("{", "").replace("}", "").strip() or None


def parse_bibtex(text: str) -> list[dict]:
    parser = bibtexparser.bparser.BibTexParser(common_strings=True, ignore_nonstandard_types=False)
    db = bibtexparser.loads(text, parser=parser)
    papers = []
    for entry in db.entries:
        authors = _clean(entry.get("author", "").replace(" and ", ", ")) if entry.get("author") else None
        year = entry.get("year")
        venue = _clean(entry.get("journal") or entry.get("booktitle") or entry.get("publisher"))
        papers.append({
            "title": _clean(entry.get("title")) or "Untitled",
            "authors": authors,
            "abstract": _clean(entry.get("abstract")),
            "year": int(year) if year and str(year).isdigit() else None,
            "venue": venue,
            "doi": normalize_doi(entry.get("doi")) or None,
            "source": "bibtex",
        })
    return papers


def parse_ris(text: str) -> list[dict]:
    entries = rispy.loads(text)
    papers = []
    for entry in entries:
        authors_list = entry.get("authors") or entry.get("first_authors") or []
        authors = ", ".join(authors_list) if authors_list else None
        year = entry.get("year") or entry.get("publication_year")
        venue = entry.get("journal_name") or entry.get("secondary_title") or entry.get("alternate_title3")
        title = entry.get("title") or entry.get("primary_title") or "Untitled"
        papers.append({
            "title": _clean(title) or "Untitled",
            "authors": _clean(authors),
            "abstract": _clean(entry.get("abstract")),
            "year": int(year) if year and str(year)[:4].isdigit() else None,
            "venue": _clean(venue),
            "doi": normalize_doi(entry.get("doi")) or None,
            "source": "ris",
        })
    return papers


def parse_file(filename: str, content: bytes) -> list[dict]:
    text = content.decode("utf-8", errors="replace")
    name = filename.lower()
    if name.endswith(".ris"):
        return parse_ris(text)
    if name.endswith(".bib") or name.endswith(".bibtex"):
        return parse_bibtex(text)
    # Sniff: RIS always starts records with "TY  - "
    if "TY  -" in text[:2000]:
        return parse_ris(text)
    return parse_bibtex(text)
