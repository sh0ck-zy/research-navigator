"""Background jobs: a jobs-table row + FastAPI BackgroundTasks. No celery.

One user, one uvicorn worker. Each job runs in a worker thread with its own
DB connection. State mutations still go through commands.apply so the event
log stays complete — the enrichment writes are actor='ai'.
"""
import json
import uuid

from backend import db
from backend.services import commands, embeddings, openalex


def create_job(project_id: str, job_type: str, total: int) -> str:
    job_id = uuid.uuid4().hex
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO jobs(id, project_id, type, progress_total) VALUES (?, ?, ?, ?)",
            (job_id, project_id, job_type, total),
        )
    return job_id


def _set(conn, job_id: str, **fields):
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE jobs SET {sets} WHERE id = ?", (*fields.values(), job_id))


def get_job(job_id: str) -> dict | None:
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return dict(row) if row else None


def running_job(project_id: str, job_type: str) -> str | None:
    with db.connect() as conn:
        row = conn.execute(
            """SELECT id FROM jobs WHERE project_id = ? AND type = ?
               AND status IN ('queued','running') ORDER BY created_at DESC LIMIT 1""",
            (project_id, job_type),
        ).fetchone()
    return row["id"] if row else None


def run_enrichment(job_id: str, project_id: str, paper_ids: list[str]) -> None:
    """Resolve DOIs via OpenAlex, fill metadata, embed. Idempotent per paper."""
    conn = db.connect()
    try:
        with conn:
            _set(conn, job_id, status="running")

        rows = conn.execute(
            "SELECT id, doi, title, abstract FROM papers WHERE id IN (%s)"
            % ",".join("?" * len(paper_ids)),
            paper_ids,
        ).fetchall()

        by_doi = {r["doi"]: r["id"] for r in rows if r["doi"]}
        resolved = openalex.fetch_by_dois(list(by_doi)) if by_doi else {}

        done = 0
        for r in rows:
            pid = r["id"]
            enriched = resolved.get(r["doi"]) if r["doi"] else None
            title = (enriched or {}).get("title") or r["title"]
            abstract = (enriched or {}).get("abstract") or r["abstract"] or ""

            update = {"type": "update_paper", "paper_id": pid}
            if enriched:
                update.update({
                    "openalex_id": enriched["openalex_id"],
                    "authors": enriched["authors"] or None,
                    "abstract": abstract or None,
                    "year": enriched["year"],
                    "venue": enriched["venue"] or None,
                    "cited_by_count": enriched["cited_by_count"],
                    "pdf_url": enriched["pdf_url"],
                    "title": title,
                })
                status = "enriched" if abstract else "no_abstract"
            else:
                status = "no_abstract" if not abstract else (
                    "enriched" if r["doi"] else "not_found"
                )
                if not r["doi"]:
                    status = "not_found"
            update["enrichment_status"] = status

            # Embed from best-available text (title-only when no abstract).
            vec = embeddings.embed_texts([embeddings.compose(title, abstract)])[0]
            update["embedding"] = embeddings.to_blob(vec)

            commands.apply(project_id, "ai", update, conn=conn)
            done += 1
            with conn:
                _set(conn, job_id, progress_done=done)

        with conn:
            _set(conn, job_id, status="done", finished_at=_now(conn))
    except Exception as e:  # noqa: BLE001 — surface any failure on the job row
        with conn:
            _set(conn, job_id, status="error", error=str(e), finished_at=_now(conn))
    finally:
        conn.close()


def _now(conn) -> str:
    return conn.execute("SELECT CURRENT_TIMESTAMP").fetchone()[0]


def finish_board_job(job_id: str, token_usage: dict | None, dropped: int) -> None:
    with db.connect() as conn:
        _set(
            conn, job_id, status="done", dropped_items=dropped,
            token_usage=json.dumps(token_usage) if token_usage else None,
            finished_at=_now(conn),
        )
