"""Job status polling."""
from fastapi import APIRouter, HTTPException

from backend.services import jobs

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}")
def get_job(job_id: str):
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(404, f"job {job_id} not found")
    return job
