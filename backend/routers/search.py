"""Within-project search: semantic (embeddings) + keyword, merged."""
from contextlib import closing

from fastapi import APIRouter, HTTPException, Query

from backend import db
from backend.routers.papers import PUBLIC_COLS, _row_to_paper
from backend.routers.projects import get_project_or_404
from backend.services import embeddings

router = APIRouter(prefix="/api/projects/{project_id}/search", tags=["search"])


@router.get("")
def search(project_id: str, q: str = Query(min_length=1, max_length=500), k: int = Query(15, ge=1, le=50)):
    with closing(db.connect()) as conn:
        get_project_or_404(conn, project_id)
        semantic = dict(embeddings.semantic_search(project_id, q, k))
        keyword_rows = conn.execute(
            f"""SELECT {PUBLIC_COLS} FROM papers
                WHERE project_id = ? AND (title LIKE ? OR authors LIKE ? OR abstract LIKE ?)""",
            (project_id, f"%{q}%", f"%{q}%", f"%{q}%"),
        ).fetchall()
        keyword_ids = {r["id"] for r in keyword_rows}

        # Union the two id sets, then hydrate.
        all_ids = set(semantic) | keyword_ids
        if not all_ids:
            return {"query": q, "results": []}
        rows = conn.execute(
            f"SELECT {PUBLIC_COLS} FROM papers WHERE id IN (%s)" % ",".join("?" * len(all_ids)),
            list(all_ids),
        ).fetchall()

    results = []
    for row in rows:
        p = _row_to_paper(row)
        pid = p["id"]
        p["score"] = semantic.get(pid)
        p["match"] = (
            "both" if pid in semantic and pid in keyword_ids
            else "semantic" if pid in semantic else "keyword"
        )
        results.append(p)
    # Semantic score first (keyword-only items last), then citations.
    results.sort(key=lambda p: (p["score"] is None, -(p["score"] or 0), -(p.get("cited_by_count") or 0)))
    return {"query": q, "results": results[:k]}
