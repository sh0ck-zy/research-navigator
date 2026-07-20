"""NAV — unified app: galaxy (explore) + research spaces (create).

    /         The galaxy (frontend/dist) — the landing page, no account
    /data/*   Map data + cluster briefs (frontend/data)
    /app/*    Research spaces SPA (frontend-app/dist, built with base /app/)
    /api/*    Projects/papers/board/search/export/jobs + /api/galaxy/*

Run with: uvicorn backend.app:app --port 8000
(The standalone galaxy app is backend.api:app on the observatory-mvp branch.)
"""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend import db

ROOT = Path(__file__).resolve().parent.parent
APP_DIST = ROOT / "frontend-app" / "dist"
GALAXY_DIST = ROOT / "frontend" / "dist"
GALAXY_DATA = ROOT / "frontend" / "data"


def create_app() -> FastAPI:
    db.migrate()
    app = FastAPI(title="NAV")

    @app.get("/api/health")
    def health():
        return {
            "ok": True,
            "board_generation_available": bool(os.environ.get("ANTHROPIC_API_KEY")),
        }

    from backend.routers import board, export, galaxy, jobs, papers, projects, search
    app.include_router(projects.router)
    app.include_router(papers.router)
    app.include_router(search.router)
    app.include_router(board.router)
    app.include_router(export.router)
    app.include_router(jobs.router)
    app.include_router(galaxy.router)

    if GALAXY_DATA.exists():
        app.mount("/data", StaticFiles(directory=GALAXY_DATA), name="galaxy-data")

    # Research spaces SPA: serve real files, else index.html so client-side
    # routes (/app/projects/:id/board) survive a refresh. Base is /app/.
    if APP_DIST.exists():
        @app.get("/app")
        @app.get("/app/{full_path:path}")
        def serve_space_app(full_path: str = ""):
            candidate = APP_DIST / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(APP_DIST / "index.html")

    # The galaxy is the landing page — mounted last so /api, /data and /app
    # win. Its assets live at /assets/* inside the galaxy dist.
    if GALAXY_DIST.exists():
        app.mount("/", StaticFiles(directory=GALAXY_DIST, html=True), name="galaxy")

    return app


app = create_app()
