"""Galaxy-wide endpoints: semantic search across the whole ML map."""
from fastapi import APIRouter, Query

from backend.services import galaxy

router = APIRouter(prefix="/api/galaxy", tags=["galaxy"])


@router.get("/search")
def search(q: str = Query(min_length=1), k: int = Query(default=15, ge=1, le=50)):
    return {"query": q, "results": galaxy.search(q, k)}
