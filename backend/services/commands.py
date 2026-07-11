"""Single write path for all navigator state.

Every mutation to projects/papers/board_items goes through apply(): it
appends the command to the events log and applies the state change in the
same transaction. Routers and background jobs build commands; nothing else
writes these tables directly. Provenance is by construction — actor is
recorded on every event, so "who changed what" is answerable forever.

Embeddings are the one exception inside command payloads: they are derived,
recomputable data, so the event records that an embedding was set, never the
vector itself (a 1.5 KB blob has no place in a JSON audit log).
"""
import json
import uuid

from backend import db


class CommandError(ValueError):
    """Invalid command or command payload."""


class NotFound(CommandError):
    """Target row does not exist."""


def apply(project_id: str, actor: str, command: dict, conn=None):
    """Append the event and apply the state change in one transaction.

    Returns the handler's result. Pass an existing connection to compose
    several commands into one caller-managed transaction (background jobs);
    otherwise a connection is opened and closed here.
    """
    if actor not in ("user", "ai"):
        raise CommandError(f"unknown actor: {actor}")
    ctype = command.get("type")
    handler = _HANDLERS.get(ctype)
    if handler is None:
        raise CommandError(f"unknown command type: {ctype}")

    own_conn = conn is None
    if own_conn:
        conn = db.connect()
    try:
        with conn:
            seq = conn.execute(
                "SELECT COALESCE(MAX(seq), 0) + 1 FROM events WHERE project_id = ?",
                (project_id,),
            ).fetchone()[0]
            conn.execute(
                "INSERT INTO events(id, project_id, seq, actor, command) VALUES (?, ?, ?, ?, ?)",
                (uuid.uuid4().hex, project_id, seq, actor,
                 json.dumps(_loggable(command), ensure_ascii=False)),
            )
            return handler(conn, project_id, command)
    finally:
        if own_conn:
            conn.close()


def _loggable(command: dict) -> dict:
    if "embedding" in command:
        command = {k: v for k, v in command.items() if k != "embedding"}
        command["embedding_set"] = True
    return command


# ── Projects ─────────────────────────────────────────────────────────────────

def _create_project(conn, project_id, cmd):
    conn.execute(
        """INSERT INTO projects(id, name, research_question, hypothesis, scope_notes)
           VALUES (?, ?, ?, ?, ?)""",
        (project_id, cmd["name"], cmd["research_question"],
         cmd.get("hypothesis"), cmd.get("scope_notes")),
    )
    return {"id": project_id}


PROJECT_FIELDS = {"name", "research_question", "hypothesis", "scope_notes"}


def _update_project(conn, project_id, cmd):
    fields = {k: cmd[k] for k in PROJECT_FIELDS if k in cmd}
    if not fields:
        raise CommandError("update_project: no updatable fields given")
    sets = ", ".join(f"{k} = ?" for k in fields)
    cur = conn.execute(
        f"UPDATE projects SET {sets}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (*fields.values(), project_id),
    )
    if cur.rowcount == 0:
        raise NotFound(f"project {project_id} not found")
    return {"id": project_id}


def _delete_project(conn, project_id, cmd):
    cur = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    if cur.rowcount == 0:
        raise NotFound(f"project {project_id} not found")
    return {"id": project_id}


# ── Papers ───────────────────────────────────────────────────────────────────

PAPER_INSERT_FIELDS = (
    "openalex_id", "doi", "title", "authors", "abstract", "year",
    "venue", "cited_by_count", "pdf_url", "source",
)


def _add_papers(conn, project_id, cmd):
    """Insert a batch of papers; DOI duplicates within the project are skipped.

    One user action (an import) = one command = one event, however many rows.
    """
    inserted, duplicates = [], []
    for paper in cmd["papers"]:
        pid = paper.get("id") or uuid.uuid4().hex
        doi = (paper.get("doi") or "").lower().removeprefix("https://doi.org/") or None
        cur = conn.execute(
            f"""INSERT INTO papers(id, project_id, {', '.join(PAPER_INSERT_FIELDS)})
                VALUES (?, ?{', ?' * len(PAPER_INSERT_FIELDS)})
                ON CONFLICT DO NOTHING""",
            (pid, project_id, paper.get("openalex_id"), doi, paper["title"],
             paper.get("authors"), paper.get("abstract"), paper.get("year"),
             paper.get("venue"), paper.get("cited_by_count"),
             paper.get("pdf_url"), paper["source"]),
        )
        if cur.rowcount:
            inserted.append(pid)
        else:
            duplicates.append(doi)
    return {"inserted": inserted, "duplicates": duplicates}


PAPER_UPDATE_FIELDS = {
    "openalex_id", "doi", "title", "authors", "abstract", "year", "venue",
    "cited_by_count", "pdf_url", "enrichment_status", "read_status", "tags",
    "embedding",
}


def _update_paper(conn, project_id, cmd):
    fields = {k: cmd[k] for k in PAPER_UPDATE_FIELDS if k in cmd}
    if not fields:
        raise CommandError("update_paper: no updatable fields given")
    if "tags" in fields:
        fields["tags"] = json.dumps(fields["tags"], ensure_ascii=False)
    sets = ", ".join(f"{k} = ?" for k in fields)
    cur = conn.execute(
        f"UPDATE papers SET {sets}, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND project_id = ?",
        (*fields.values(), cmd["paper_id"], project_id),
    )
    if cur.rowcount == 0:
        raise NotFound(f"paper {cmd['paper_id']} not found in project {project_id}")
    return {"id": cmd["paper_id"]}


def _delete_paper(conn, project_id, cmd):
    cur = conn.execute(
        "DELETE FROM papers WHERE id = ? AND project_id = ?",
        (cmd["paper_id"], project_id),
    )
    if cur.rowcount == 0:
        raise NotFound(f"paper {cmd['paper_id']} not found in project {project_id}")
    return {"id": cmd["paper_id"]}


# ── Board items ──────────────────────────────────────────────────────────────

def _create_board_item(conn, project_id, cmd):
    item_id = cmd.get("id") or uuid.uuid4().hex
    conn.execute(
        """INSERT INTO board_items
           (id, project_id, kind, parent_id, text, provenance, status, generation_id, position)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (item_id, project_id, cmd["kind"], cmd.get("parent_id"), cmd["text"],
         cmd["provenance"], cmd.get("status", "proposed"),
         cmd.get("generation_id"), cmd.get("position", 0)),
    )
    for link in cmd.get("papers", []):
        conn.execute(
            """INSERT OR IGNORE INTO board_item_papers(item_id, paper_id, quote, quote_valid)
               VALUES (?, ?, ?, ?)""",
            (item_id, link["paper_id"], link.get("quote"), link.get("quote_valid")),
        )
    return {"id": item_id}


def _update_board_item(conn, project_id, cmd):
    fields = {}
    if "status" in cmd:
        fields["status"] = cmd["status"]
    if "text" in cmd:
        fields["text"] = cmd["text"]
        # A user rewriting AI text takes ownership of it.
        fields["provenance"] = cmd.get("provenance", "user_edited")
    if "position" in cmd:
        fields["position"] = cmd["position"]
    if not fields:
        raise CommandError("update_board_item: no updatable fields given")
    sets = ", ".join(f"{k} = ?" for k in fields)
    cur = conn.execute(
        f"UPDATE board_items SET {sets}, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND project_id = ?",
        (*fields.values(), cmd["item_id"], project_id),
    )
    if cur.rowcount == 0:
        raise NotFound(f"board item {cmd['item_id']} not found in project {project_id}")
    return {"id": cmd["item_id"]}


def _delete_board_item(conn, project_id, cmd):
    cur = conn.execute(
        "DELETE FROM board_items WHERE id = ? AND project_id = ?",
        (cmd["item_id"], project_id),
    )
    if cur.rowcount == 0:
        raise NotFound(f"board item {cmd['item_id']} not found in project {project_id}")
    return {"id": cmd["item_id"]}


def _delete_proposed_generation(conn, project_id, cmd):
    """Clear a prior generation's still-proposed AI items before regenerating.

    Accepted/rejected/user items are never touched — the user acted on those.
    """
    cur = conn.execute(
        """DELETE FROM board_items
           WHERE project_id = ? AND provenance = 'ai_suggested' AND status = 'proposed'""",
        (project_id,),
    )
    return {"deleted": cur.rowcount}


_HANDLERS = {
    "create_project": _create_project,
    "update_project": _update_project,
    "delete_project": _delete_project,
    "add_papers": _add_papers,
    "update_paper": _update_paper,
    "delete_paper": _delete_paper,
    "create_board_item": _create_board_item,
    "update_board_item": _update_board_item,
    "delete_board_item": _delete_board_item,
    "delete_proposed_generation": _delete_proposed_generation,
}
