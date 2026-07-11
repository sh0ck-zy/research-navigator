"""Research Navigator API.

Project-based workspaces: library of papers + AI-drafted Living Research
Board. Run with: uvicorn backend.app:app --port 8000
(The parked galaxy app is backend.api:app on the observatory-mvp branch.)
"""
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend import db

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIST = ROOT / "frontend-app" / "dist"


def create_app() -> FastAPI:
    db.migrate()
    app = FastAPI(title="Research Navigator API")

    @app.get("/api/health")
    def health():
        return {
            "ok": True,
            "board_generation_available": bool(os.environ.get("ANTHROPIC_API_KEY")),
        }

    from backend.routers import board, export, jobs, papers, projects, search
    app.include_router(projects.router)
    app.include_router(papers.router)
    app.include_router(search.router)
    app.include_router(board.router)
    app.include_router(export.router)
    app.include_router(jobs.router)

    # Production serves the built React app; during development run
    # `npm run dev` in frontend-app/ (it proxies /api to 127.0.0.1:8000).
    if FRONTEND_DIST.exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        # SPA fallback: serve a real file if it exists, else index.html so
        # client-side routes (e.g. /projects/:id/library) survive a refresh.
        # /api/* is excluded so unknown API paths still 404 as JSON.
        @app.get("/{full_path:path}")
        def serve_spa(full_path: str):
            if full_path.startswith("api/"):
                raise HTTPException(404, "Not Found")
            candidate = FRONTEND_DIST / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(FRONTEND_DIST / "index.html")

    return app


app = create_app()
