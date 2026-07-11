"""Living Research Board: read, generate (AI), and user CRUD. Writes via commands.apply."""
import json
import os
from contextlib import closing

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from backend import db
from backend.routers.projects import get_project_or_404
from backend.services import board_generator, commands, jobs

router = APIRouter(prefix="/api/projects/{project_id}/board", tags=["board"])

KINDS = ("concept", "claim", "evidence_support", "evidence_contradiction",
         "open_question", "next_action")


@router.get("")
def get_board(project_id: str):
    with closing(db.connect()) as conn:
        get_project_or_404(conn, project_id)
        items = [dict(r) for r in conn.execute(
            "SELECT * FROM board_items WHERE project_id = ? ORDER BY position, created_at",
            (project_id,),
        ).fetchall()]
        links = conn.execute(
            """SELECT bip.item_id, bip.quote, bip.quote_valid,
                      p.id AS paper_id, p.title, p.doi, p.year, p.authors
               FROM board_item_papers bip JOIN papers p ON p.id = bip.paper_id
               WHERE p.project_id = ?""",
            (project_id,),
        ).fetchall()
        last_job = conn.execute(
            """SELECT id, status, token_usage, dropped_items, finished_at FROM jobs
               WHERE project_id = ? AND type = 'generate_board'
               ORDER BY created_at DESC LIMIT 1""",
            (project_id,),
        ).fetchone()

    by_item: dict[str, list] = {}
    for l in links:
        by_item.setdefault(l["item_id"], []).append({
            "paper_id": l["paper_id"], "title": l["title"], "doi": l["doi"],
            "year": l["year"], "authors": l["authors"],
            "quote": l["quote"], "quote_valid": bool(l["quote_valid"]) if l["quote_valid"] is not None else None,
        })
    for it in items:
        it["papers"] = by_item.get(it["id"], [])

    meta = dict(last_job) if last_job else None
    if meta and meta.get("token_usage"):
        meta["token_usage"] = json.loads(meta["token_usage"])
    return {"items": items, "last_generation": meta}


@router.post("/generate", status_code=202)
def generate_board(project_id: str, background_tasks: BackgroundTasks, body: dict | None = None):
    with closing(db.connect()) as conn:
        get_project_or_404(conn, project_id)
        all_ids = [r["id"] for r in conn.execute(
            "SELECT id FROM papers WHERE project_id = ?", (project_id,)).fetchall()]

    paper_ids = (body or {}).get("paper_ids")
    selected = paper_ids if paper_ids else all_ids
    if not selected:
        raise HTTPException(422, "no papers to generate a board from")
    if len(selected) > board_generator.MAX_PAPERS:
        raise HTTPException(
            400, f"select at most {board_generator.MAX_PAPERS} papers to generate a board "
                 f"(you selected {len(selected)}). Filter by tag, status, or search first.")
    if jobs.running_job(project_id, "generate_board"):
        raise HTTPException(409, "a board generation is already running for this project")
    # Capability check last: the request is valid, the server just isn't configured.
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(
            503, "ANTHROPIC_API_KEY is not set — board generation is disabled. Everything else works.")

    job_id = jobs.create_job(project_id, "generate_board", len(selected))
    background_tasks.add_task(board_generator.generate, job_id, project_id, paper_ids)
    return {"job_id": job_id}


class BoardItemCreate(BaseModel):
    kind: str
    text: str = Field(min_length=1, max_length=2000)
    parent_id: str | None = None
    paper_ids: list[str] = []


@router.post("/items", status_code=201)
def create_item(project_id: str, body: BoardItemCreate):
    if body.kind not in KINDS:
        raise HTTPException(422, f"kind must be one of {KINDS}")
    with closing(db.connect()) as conn:
        get_project_or_404(conn, project_id)
    result = commands.apply(project_id, "user", {
        "type": "create_board_item", "kind": body.kind, "text": body.text,
        "provenance": "user_created", "status": "accepted",
        "parent_id": body.parent_id,
        "papers": [{"paper_id": pid} for pid in body.paper_ids],
    })
    return {"id": result["id"]}


class BoardItemUpdate(BaseModel):
    status: str | None = None
    text: str | None = Field(default=None, min_length=1, max_length=2000)


@router.patch("/items/{item_id}")
def update_item(project_id: str, item_id: str, body: BoardItemUpdate):
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(422, "no fields to update")
    if "status" in fields and fields["status"] not in ("proposed", "accepted", "rejected"):
        raise HTTPException(422, "status must be proposed|accepted|rejected")
    try:
        commands.apply(project_id, "user", {"type": "update_board_item", "item_id": item_id, **fields})
    except commands.NotFound as e:
        raise HTTPException(404, str(e))
    return {"ok": True, "id": item_id}


@router.delete("/items/{item_id}")
def delete_item(project_id: str, item_id: str):
    try:
        commands.apply(project_id, "user", {"type": "delete_board_item", "item_id": item_id})
    except commands.NotFound as e:
        raise HTTPException(404, str(e))
    return {"ok": True, "id": item_id}
