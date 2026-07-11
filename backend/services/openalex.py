"""OpenAlex client shared by the pipeline and the navigator.

`reconstruct_abstract` and `parse_work` are the single source of truth for
turning an OpenAlex work into our paper dict — pipeline/ingest.py imports
them from here. The fetch_* helpers are navigator-specific (resolve a DOI,
URL, or arXiv id into a work).
"""
import re
import time
import xml.etree.ElementTree as ET

import requests

OPENALEX_WORKS = "https://api.openalex.org/works"
ARXIV_API = "http://export.arxiv.org/api/query"
USER_AGENT = "ClarityResearch/0.1 (mailto:clarity@example.com)"
SELECT = (
    "id,title,publication_year,cited_by_count,authorships,concepts,"
    "abstract_inverted_index,doi,primary_location"
)


def reconstruct_abstract(inverted_index: dict) -> str:
    """Reconstruct abstract text from OpenAlex inverted index format."""
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort()
    return " ".join(word for _, word in word_positions)


def normalize_doi(doi: str | None) -> str:
    """Bare lowercase DOI, no scheme/host. '' for falsy input."""
    if not doi:
        return ""
    doi = doi.strip().lower()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    return doi


def parse_work(work: dict) -> dict:
    """Turn one OpenAlex work into our paper dict.

    Keys match both the pipeline output and the navigator papers table.
    Unlike the pipeline, we keep the OA pdf_url (needed for v0.2 grounding)
    and do NOT drop abstract-less works — the caller decides.
    """
    authors = ", ".join(
        a["author"]["display_name"]
        for a in (work.get("authorships") or [])
        if a.get("author", {}).get("display_name")
    )
    abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
    categories = " ".join(
        c["display_name"]
        for c in (work.get("concepts") or [])[:5]
        if c.get("display_name")
    )
    primary = work.get("primary_location") or {}
    venue = ((primary.get("source") or {}).get("display_name")) or ""
    pdf_url = primary.get("pdf_url") or None
    return {
        "openalex_id": (work.get("id") or "").replace("https://openalex.org/", "") or None,
        "title": work.get("title") or "Untitled",
        "authors": authors,
        "abstract": abstract,
        "year": work.get("publication_year"),
        "cited_by_count": work.get("cited_by_count", 0),
        "categories": categories,
        "doi": normalize_doi(work.get("doi")),
        "venue": venue,
        "pdf_url": pdf_url,
    }


def _get(params: dict, path: str = "") -> dict | None:
    """One GET with a short retry. Returns parsed JSON or None on failure."""
    url = OPENALEX_WORKS + path
    for attempt in range(3):
        try:
            resp = requests.get(
                url, params={**params, "mailto": "clarity@example.com"},
                headers={"User-Agent": USER_AGENT}, timeout=20,
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            if attempt == 2:
                return None
            time.sleep(1.5 * (attempt + 1))
    return None


def fetch_by_doi(doi: str) -> dict | None:
    norm = normalize_doi(doi)
    # arXiv DOIs (10.48550/arXiv.<id>) are unreliable in OpenAlex — go to arXiv.
    if m := re.match(r"10\.48550/arxiv\.(.+)$", norm):
        return fetch_by_arxiv(m.group(1))
    work = _get({"select": SELECT}, path=f"/https://doi.org/{norm}")
    return parse_work(work) if work else None


def fetch_by_dois(dois: list[str]) -> dict[str, dict]:
    """Batch-resolve DOIs (50 per request). Returns {normalized_doi: paper}."""
    out: dict[str, dict] = {}
    clean = [normalize_doi(d) for d in dois if normalize_doi(d)]
    for i in range(0, len(clean), 50):
        chunk = clean[i:i + 50]
        filt = "doi:" + "|".join(chunk)
        data = _get({"filter": filt, "select": SELECT, "per_page": 50})
        for work in (data or {}).get("results", []):
            paper = parse_work(work)
            if paper["doi"]:
                out[paper["doi"]] = paper
        time.sleep(0.1)
    return out


def fetch_by_openalex_id(oa_id: str) -> dict | None:
    oa_id = oa_id.replace("https://openalex.org/", "").strip()
    work = _get({"select": SELECT}, path=f"/{oa_id}")
    return parse_work(work) if work else None


_ARXIV_NS = {"a": "http://www.w3.org/2005/Atom"}


def fetch_by_arxiv(arxiv_id: str) -> dict | None:
    """Resolve an arXiv id via the arXiv API.

    OpenAlex is unreliable for preprints (older arXiv DOIs aren't indexed),
    but arXiv itself always has title/abstract/authors — exactly what the
    board needs. Citations/venue are absent for a preprint (left empty).
    """
    arxiv_id = arxiv_id.strip()
    try:
        resp = requests.get(
            ARXIV_API, params={"id_list": arxiv_id, "max_results": 1},
            headers={"User-Agent": USER_AGENT}, timeout=20,
        )
        resp.raise_for_status()
        entry = ET.fromstring(resp.text).find("a:entry", _ARXIV_NS)
    except (requests.RequestException, ET.ParseError):
        return None
    if entry is None or entry.find("a:title", _ARXIV_NS) is None:
        return None

    def text(tag: str) -> str:
        el = entry.find(f"a:{tag}", _ARXIV_NS)
        return " ".join(el.text.split()) if el is not None and el.text else ""

    authors = ", ".join(
        " ".join(n.text.split())
        for a in entry.findall("a:author", _ARXIV_NS)
        if (n := a.find("a:name", _ARXIV_NS)) is not None and n.text
    )
    published = text("published")
    year = int(published[:4]) if published[:4].isdigit() else None
    doi_el = entry.find("{http://arxiv.org/schemas/atom}doi")
    return {
        "openalex_id": None,
        "title": text("title") or "Untitled",
        "authors": authors,
        "abstract": text("summary"),
        "year": year,
        "cited_by_count": None,
        "categories": "",
        "doi": normalize_doi(doi_el.text) if doi_el is not None and doi_el.text else "",
        "venue": "arXiv",
        "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}",
    }


def resolve_url(url: str) -> dict | None:
    """Best-effort resolve of a pasted URL (OpenAlex / DOI / arXiv)."""
    url = url.strip()
    if m := re.search(r"openalex\.org/(W\d+)", url, re.I):
        return fetch_by_openalex_id(m.group(1))
    if m := re.search(r"arxiv\.org/(?:abs|pdf)/([\d.]+)", url, re.I):
        return fetch_by_arxiv(m.group(1))
    if m := re.search(r"(?:doi\.org/|^)(10\.\d{4,}/\S+)", url, re.I):
        return fetch_by_doi(m.group(1))
    return None
