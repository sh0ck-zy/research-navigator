"""Projects CRUD. All writes go through commands.apply — see services/commands.py."""
import uuid
from contextlib import closing

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend import db
from backend.services import commands

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    research_question: str = Field(min_length=1, max_length=2000)
    hypothesis: str | None = Field(default=None, max_length=2000)
    scope_notes: str | None = Field(default=None, max_length=5000)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    research_question: str | None = Field(default=None, min_length=1, max_length=2000)
    hypothesis: str | None = Field(default=None, max_length=2000)
    scope_notes: str | None = Field(default=None, max_length=5000)


def get_project_or_404(conn, project_id: str) -> dict:
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row is None:
        raise HTTPException(404, f"project {project_id} not found")
    return dict(row)


@router.get("")
def list_projects():
    with closing(db.connect()) as conn:
        rows = conn.execute(
            """SELECT p.*,
                      (SELECT COUNT(*) FROM papers WHERE project_id = p.id) AS paper_count,
                      (SELECT COUNT(*) FROM board_items WHERE project_id = p.id) AS board_item_count
               FROM projects p ORDER BY updated_at DESC"""
        ).fetchall()
    return {"projects": [dict(r) for r in rows]}


@router.post("", status_code=201)
def create_project(body: ProjectCreate):
    project_id = uuid.uuid4().hex
    commands.apply(project_id, "user", {"type": "create_project", **body.model_dump()})
    with closing(db.connect()) as conn:
        return get_project_or_404(conn, project_id)


class FromClusterCreate(BaseModel):
    cluster_id: int
    research_question: str = Field(min_length=1, max_length=2000)
    name: str | None = Field(default=None, max_length=200)
    max_papers: int = Field(default=300, ge=1, le=600)


@router.post("/from-cluster", status_code=201)
def create_project_from_cluster(body: FromClusterCreate):
    """The galaxy → space bridge: seed a Research Space from a map cluster.

    Papers come from the ML corpus with their precomputed MiniLM vectors
    (L2-normalized on copy, same as scripts/seed_demo.py), so semantic
    search works immediately and no enrichment job is needed.
    """
    from backend.services import galaxy

    if body.cluster_id not in galaxy.cluster_ids():
        raise HTTPException(404, f"cluster {body.cluster_id} not found")
    cname = galaxy.cluster_name(body.cluster_id)
    picked = galaxy.cluster_papers(body.cluster_id)[: body.max_papers]

    project_id = uuid.uuid4().hex
    commands.apply(project_id, "user", {
        "type": "create_project",
        "name": body.name or cname,
        "research_question": body.research_question,
        "hypothesis": None,
        "scope_notes": (
            f"Seeded from the Machine Learning galaxy — cluster "
            f"'{cname}' ({len(picked)} most central papers)."
        ),
    })
    rows = [{k: p[k] for k in commands.PAPER_INSERT_FIELDS} for p in picked]
    result = commands.apply(project_id, "user", {"type": "add_papers", "papers": rows})

    with closing(db.connect()) as conn:
        db_rows = conn.execute(
            "SELECT id, openalex_id FROM papers WHERE project_id = ?", (project_id,)
        ).fetchall()
    row_by_oa = {p["openalex_id"]: p["row"] for p in picked}
    for r in db_rows:
        row = row_by_oa.get(r["openalex_id"])
        if row is None:
            continue
        commands.apply(project_id, "ai", {
            "type": "update_paper", "paper_id": r["id"],
            "embedding": galaxy.embedding_row(row).tobytes(),
            "enrichment_status": "enriched",
        })

    return {
        "project_id": project_id,
        "paper_count": len(result["inserted"]),
        "board_url": f"/app/projects/{project_id}/board",
    }


@router.get("/{project_id}")
def get_project(project_id: str):
    with closing(db.connect()) as conn:
        project = get_project_or_404(conn, project_id)
        counts = conn.execute(
            """SELECT
                 (SELECT COUNT(*) FROM papers WHERE project_id = ?) AS paper_count,
                 (SELECT COUNT(*) FROM board_items WHERE project_id = ?) AS board_item_count""",
            (project_id, project_id),
        ).fetchone()
    return {**project, **dict(counts)}


@router.patch("/{project_id}")
def update_project(project_id: str, body: ProjectUpdate):
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(422, "no fields to update")
    try:
        commands.apply(project_id, "user", {"type": "update_project", **fields})
    except commands.NotFound as e:
        raise HTTPException(404, str(e))
    with closing(db.connect()) as conn:
        return get_project_or_404(conn, project_id)


@router.delete("/{project_id}")
def delete_project(project_id: str):
    try:
        commands.apply(project_id, "user", {"type": "delete_project"})
    except commands.NotFound as e:
        raise HTTPException(404, str(e))
    return {"ok": True, "id": project_id}
