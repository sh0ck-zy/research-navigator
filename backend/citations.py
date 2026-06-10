"""BibTeX generation — mirror of frontend/src/bibtex.js (keep both in sync).

Used by the /api/library/export.bib endpoint so the whole saved library can be
downloaded as a .bib file. Per-paper "Cite" in the UI is generated client-side.
"""
import re


def format_authors(authors_str: str) -> str:
    """'First Last, First M Last' -> 'Last, First and Last, First M'."""
    if not authors_str:
        return ""
    out = []
    for name in authors_str.split(","):
        name = name.strip()
        if not name:
            continue
        parts = name.split()
        if len(parts) == 1:
            out.append(parts[0])
        else:
            family = parts[-1]
            given = " ".join(parts[:-1])
            out.append(f"{family}, {given}")
    return " and ".join(out)


def cite_key(paper: dict) -> str:
    authors = paper.get("authors") or ""
    first = authors.split(",")[0].strip() if authors else ""
    family = first.split()[-1] if first else ""
    year = paper.get("year") or ""
    key = re.sub(r"[^A-Za-z0-9]", "", f"{family}{year}")
    return key or (paper.get("id") or paper.get("paper_id") or "ref")


def bibtex(paper: dict) -> str:
    key = cite_key(paper)
    title = paper.get("title") or "Untitled"
    authors = format_authors(paper.get("authors") or "")
    year = str(paper.get("year") or "")
    doi = paper.get("doi") or ""
    venue = paper.get("venue") or ""
    oaid = paper.get("id") or paper.get("paper_id") or ""

    fields = [f"  title = {{{title}}}"]
    if authors:
        fields.append(f"  author = {{{authors}}}")
    if year:
        fields.append(f"  year = {{{year}}}")

    if venue:
        entry = "article"
        fields.append(f"  journal = {{{venue}}}")
    else:
        entry = "misc"
        if oaid:
            fields.append(f"  howpublished = {{\\url{{https://openalex.org/{oaid}}}}}")
    if doi:
        fields.append(f"  doi = {{{doi}}}")
    if oaid and entry == "misc":
        fields.append(f"  note = {{OpenAlex: {oaid}}}")

    body = ",\n".join(fields)
    return f"@{entry}{{{key},\n{body}\n}}"


def bibtex_for_many(papers: list[dict]) -> str:
    return "\n\n".join(bibtex(p) for p in papers)
