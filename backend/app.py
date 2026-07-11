"""Research Navigator API.

Project-based workspaces: library of papers + AI-drafted Living Research
Board. Run with: uvicorn backend.app:app --port 8000
(The parked galaxy app is backend.api:app on the observatory-mvp branch.)
"""
import os
from pathlib import Path

from fastapi import FastAPI
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

    from backend.routers import projects
    app.include_router(projects.router)

    # Production serves the built React app; during development run
    # `npm run dev` in frontend-app/ (it proxies /api to 127.0.0.1:8000).
    if FRONTEND_DIST.exists():
        @app.get("/")
        def serve_index():
            return FileResponse(FRONTEND_DIST / "index.html")

        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="static")

    return app


app = create_app()
