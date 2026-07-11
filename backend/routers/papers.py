"""Papers: import, add, list, update, delete, search. Writes via commands.apply."""
import json
from contextlib import closing

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from backend import db
from backend.routers.projects import get_project_or_404
from backend.services import commands, embeddings, imports, jobs, openalex

router = APIRouter(prefix="/api/projects/{project_id}/papers", tags=["papers"])

PUBLIC_COLS = (
    "id, project_id, openalex_id, doi, title, authors, abstract, year, venue, "
    "cited_by_count, pdf_url, source, enrichment_status, read_status, tags, "
    "added_at, updated_at"
)


def _row_to_paper(row) -> dict:
    p = dict(row)
    p["tags"] = json.loads(p.get("tags") or "[]")
    p["has_embedding"] = row["has_embedding"] if "has_embedding" in row.keys() else None
    return p


def _kick_enrichment(project_id: str, paper_ids: list[str], bg: BackgroundTasks) -> str | None:
    if not paper_ids:
        return None
    job_id = jobs.create_job(project_id, "enrich", len(paper_ids))
    bg.add_task(jobs.run_enrichment, job_id, project_id, paper_ids)
    return job_id


# ── Import a .bib/.ris file ───────────────────────────────────────────────────

@router.post("/import")
async def import_file(
    project_id: str, file: UploadFile, background_tasks: BackgroundTasks
):
    with closing(db.connect()) as conn:
        get_project_or_404(conn, project_id)

    content = await file.read()
    try:
        parsed = imports.parse_file(file.filename or "upload.bib", content)
    except Exception as e:  # noqa: BLE001 — malformed upload
        raise HTTPException(422, f"could not parse file: {e}")

    if not parsed:
        return {"imported": 0, "duplicates": 0, "errors": ["no entries found"], "enrich_job_id": None}

    result = commands.apply(project_id, "user", {"type": "add_papers", "papers": parsed})
    inserted = result["inserted"]
    job_id = _kick_enrichment(project_id, inserted, background_tasks)
    return {
        "imported": len(inserted),
        "duplicates": len(result["duplicates"]),
        "errors": [],
        "enrich_job_id": job_id,
    }


# ── Add a single paper by DOI or URL (synchronous resolve) ────────────────────

class AddPaper(BaseModel):
    doi: str | None = None
    url: str | None = None


@router.post("", status_code=201)
def add_paper(project_id: str, body: AddPaper):
    with closing(db.connect()) as conn:
        get_project_or_404(conn, project_id)

    if body.doi:
        enriched = openalex.fetch_by_doi(body.doi)
    elif body.url:
        enriched = openalex.resolve_url(body.url)
    else:
        raise HTTPException(422, "provide a doi or url")
    if enriched is None:
        raise HTTPException(404, "could not resolve that DOI/URL on OpenAlex")

    source = "doi" if body.doi else "url"
    paper = {**enriched, "source": source}
    result = commands.apply(project_id, "user", {"type": "add_papers", "papers": [paper]})
    if not result["inserted"]:
        raise HTTPException(409, "paper already in this project")
    pid = result["inserted"][0]

    # Embed inline — a single paper is fast and the user is waiting.
    vec = embeddings.embed_texts([embeddings.compose(enriched["title"], enriched["abstract"])])[0]
    status = "enriched" if enriched["abstract"] else "no_abstract"
    commands.apply(project_id, "ai", {
        "type": "update_paper", "paper_id": pid,
        "embedding": embeddings.to_blob(vec), "enrichment_status": status,
    })
    with closing(db.connect()) as conn:
        row = conn.execute(
            f"SELECT {PUBLIC_COLS} FROM papers WHERE id = ?", (pid,)
        ).fetchone()
    return _row_to_paper(row)


# ── List / filter ─────────────────────────────────────────────────────────────

@router.get("")
def list_papers(
    project_id: str,
    status: str | None = None,
    tag: str | None = None,
    q: str | None = Query(default=None, description="keyword filter over title/authors/abstract"),
):
    clauses, params = ["project_id = ?"], [project_id]
    if status:
        clauses.append("read_status = ?")
        params.append(status)
    if q:
        clauses.append("(title LIKE ? OR authors LIKE ? OR abstract LIKE ?)")
        params += [f"%{q}%"] * 3
    where = " AND ".join(clauses)
    with closing(db.connect()) as conn:
        rows = conn.execute(
            f"SELECT {PUBLIC_COLS}, (embedding IS NOT NULL) AS has_embedding "
            f"FROM papers WHERE {where} ORDER BY cited_by_count DESC NULLS LAST, added_at DESC",
            params,
        ).fetchall()
    papers = [_row_to_paper(r) for r in rows]
    if tag:
        papers = [p for p in papers if tag in p["tags"]]
    return {"papers": papers}


# ── Update read-status / tags ─────────────────────────────────────────────────

class PaperUpdate(BaseModel):
    read_status: str | None = Field(default=None)
    tags: list[str] | None = None


@router.patch("/{paper_id}")
def update_paper(project_id: str, paper_id: str, body: PaperUpdate):
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(422, "no fields to update")
    try:
        commands.apply(project_id, "user", {"type": "update_paper", "paper_id": paper_id, **fields})
    except commands.NotFound as e:
        raise HTTPException(404, str(e))
    with closing(db.connect()) as conn:
        row = conn.execute(f"SELECT {PUBLIC_COLS} FROM papers WHERE id = ?", (paper_id,)).fetchone()
    return _row_to_paper(row)


@router.delete("/{paper_id}")
def delete_paper(project_id: str, paper_id: str):
    try:
        commands.apply(project_id, "user", {"type": "delete_paper", "paper_id": paper_id})
    except commands.NotFound as e:
        raise HTTPException(404, str(e))
    return {"ok": True, "id": paper_id}
