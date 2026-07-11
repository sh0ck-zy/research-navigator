"""SQLite layer for the Research Navigator (data/navigator.db).

Separate from the galaxy's library.db on purpose: the navigator is
project-scoped and event-sourced; library.db is a flat global list tied to
the parked map. Migrations are an ordered list of SQL scripts tracked in
schema_migrations — append new scripts, never edit applied ones.
"""
import sqlite3
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "navigator.db"

MIGRATIONS: list[str] = [
    # 001 — initial schema
    """
    CREATE TABLE projects(
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        research_question TEXT NOT NULL,
        hypothesis TEXT,
        scope_notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE papers(
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        openalex_id TEXT,
        doi TEXT,
        title TEXT NOT NULL,
        authors TEXT,
        abstract TEXT,
        year INTEGER,
        venue TEXT,
        cited_by_count INTEGER,
        pdf_url TEXT,
        source TEXT NOT NULL CHECK(source IN ('bibtex','ris','doi','url','seed')),
        enrichment_status TEXT NOT NULL DEFAULT 'pending'
            CHECK(enrichment_status IN ('pending','enriched','not_found','no_abstract')),
        read_status TEXT NOT NULL DEFAULT 'unread'
            CHECK(read_status IN ('unread','reading','read','important','rejected')),
        tags TEXT NOT NULL DEFAULT '[]',
        embedding BLOB,
        added_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE UNIQUE INDEX idx_papers_project_doi ON papers(project_id, doi)
        WHERE doi IS NOT NULL AND doi != '';
    CREATE INDEX idx_papers_project ON papers(project_id);

    CREATE TABLE board_items(
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        kind TEXT NOT NULL CHECK(kind IN
            ('concept','claim','evidence_support','evidence_contradiction',
             'open_question','next_action')),
        parent_id TEXT REFERENCES board_items(id) ON DELETE CASCADE,
        text TEXT NOT NULL,
        provenance TEXT NOT NULL CHECK(provenance IN ('ai_suggested','user_created','user_edited')),
        status TEXT NOT NULL DEFAULT 'proposed' CHECK(status IN ('proposed','accepted','rejected')),
        generation_id TEXT,
        position INTEGER NOT NULL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX idx_board_items_project ON board_items(project_id);

    CREATE TABLE board_item_papers(
        item_id TEXT NOT NULL REFERENCES board_items(id) ON DELETE CASCADE,
        paper_id TEXT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
        quote TEXT,
        quote_valid INTEGER,
        PRIMARY KEY(item_id, paper_id)
    );

    CREATE TABLE jobs(
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('enrich','generate_board')),
        status TEXT NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','running','done','error')),
        progress_done INTEGER NOT NULL DEFAULT 0,
        progress_total INTEGER NOT NULL DEFAULT 0,
        error TEXT,
        token_usage TEXT,
        dropped_items INTEGER NOT NULL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        finished_at TEXT
    );

    -- Append-only audit of every mutation. No FK to projects: the log must
    -- survive project deletion.
    CREATE TABLE events(
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        seq INTEGER NOT NULL,
        actor TEXT NOT NULL CHECK(actor IN ('user','ai')),
        command TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(project_id, seq)
    );
    """,
]


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def migrate() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect()) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations(
                version INTEGER PRIMARY KEY,
                applied_at TEXT DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        applied = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
        for version, script in enumerate(MIGRATIONS, start=1):
            if version in applied:
                continue
            conn.executescript(script)
            with conn:
                conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))
            print(f"[db] applied migration {version:03d}")
