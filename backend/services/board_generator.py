"""Generate a Living Research Board draft from a project's papers (Claude).

The model reads the research question + up to 100 papers' titles/abstracts and
proposes typed, citation-linked knowledge objects. Every AI item is validated
server-side: it must cite a real paper, and evidence must quote the cited
abstract verbatim (ADR-003 — AI augments, never invents). Unverifiable items
are dropped and counted, never shown.

Model default is claude-sonnet-5 (env-overridable). Adaptive thinking is on by
default on Sonnet 5 and sampling params are rejected, so we send neither. We
stream to avoid HTTP timeouts on the large structured output.
"""
import json
import os
import re
import uuid

from backend import db
from backend.services import commands, jobs

MODEL = os.environ.get("NAVIGATOR_MODEL", "claude-sonnet-5")
MAX_PAPERS = 100
ABSTRACT_BUDGET = 1500  # chars per abstract in the prompt

BOARD_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "concepts": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "text": {"type": "string"},
                    "papers": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text", "papers"],
            },
        },
        "claims": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "text": {"type": "string"},
                    "papers": {"type": "array", "items": {"type": "string"}},
                    "supporting": {"type": "array", "items": {
                        "type": "object", "additionalProperties": False,
                        "properties": {
                            "text": {"type": "string"},
                            "papers": {"type": "array", "items": {"type": "string"}},
                            "quote": {"type": "string"},
                        },
                        "required": ["text", "papers", "quote"],
                    }},
                    "contradicting": {"type": "array", "items": {
                        "type": "object", "additionalProperties": False,
                        "properties": {
                            "text": {"type": "string"},
                            "papers": {"type": "array", "items": {"type": "string"}},
                            "quote": {"type": "string"},
                        },
                        "required": ["text", "papers", "quote"],
                    }},
                },
                "required": ["text", "papers", "supporting", "contradicting"],
            },
        },
        "open_questions": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "text": {"type": "string"},
                    "papers": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text", "papers"],
            },
        },
        "next_actions": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
    },
    "required": ["concepts", "claims", "open_questions", "next_actions"],
}


def _norm(s: str) -> str:
    """Lowercase + collapse whitespace, for substring quote matching."""
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def _load_papers(project_id: str, paper_ids: list[str] | None) -> list[dict]:
    with db.connect() as conn:
        if paper_ids:
            rows = conn.execute(
                "SELECT id, title, abstract FROM papers WHERE project_id = ? AND id IN (%s)"
                % ",".join("?" * len(paper_ids)),
                (project_id, *paper_ids),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, title, abstract FROM papers WHERE project_id = ? "
                "ORDER BY cited_by_count DESC NULLS LAST",
                (project_id,),
            ).fetchall()
    return [dict(r) for r in rows]


def _existing_board(project_id: str) -> list[str]:
    """Accepted/user items, so regeneration proposes deltas, not restatements."""
    with db.connect() as conn:
        rows = conn.execute(
            """SELECT text FROM board_items
               WHERE project_id = ? AND (status = 'accepted'
                     OR provenance IN ('user_created','user_edited'))""",
            (project_id,),
        ).fetchall()
    return [r["text"] for r in rows]


def build_prompt(project: dict, papers: list[dict], existing: list[str]) -> str:
    lines = [
        f"Research question: {project['research_question']}",
    ]
    if project.get("hypothesis"):
        lines.append(f"Working hypothesis: {project['hypothesis']}")
    if project.get("scope_notes"):
        lines.append(f"Scope: {project['scope_notes']}")
    lines.append("")
    lines.append(
        "You are reading only TITLES and ABSTRACTS, not full texts. Assert only "
        "what an abstract explicitly reports. Draft a research board of concepts, "
        "claims, supporting and contradicting evidence, open questions, and next "
        "actions. Every concept/claim/evidence item must cite the papers it comes "
        "from using their [P#] labels. Each evidence item must additionally quote "
        "a short VERBATIM span copied exactly from the cited paper's abstract."
    )
    if existing:
        lines.append("")
        lines.append(
            "The board already contains these items (accepted or written by the "
            "user). Propose only NEW or complementary items; do not restate these:"
        )
        for t in existing:
            lines.append(f"- {t}")
    lines.append("")
    lines.append("Papers:")
    for i, p in enumerate(papers, start=1):
        abstract = (p.get("abstract") or "").strip()[:ABSTRACT_BUDGET] or "(no abstract)"
        lines.append(f"[P{i}] {p['title']}\n{abstract}")
    return "\n\n".join(lines)


def _validate_and_persist(project_id, generation_id, data, papers, job_id):
    """Map [P#] refs to paper ids, drop uncited/unquoted items, insert survivors."""
    label_to_id = {f"P{i}": p["id"] for i, p in enumerate(papers, start=1)}
    abstracts = {p["id"]: _norm(p.get("abstract") or "") for p in papers}
    dropped = 0
    pos = 0

    def resolve(refs: list[str]) -> list[str]:
        return [label_to_id[r] for r in refs if r in label_to_id]

    def add_item(kind, text, paper_ids, quote=None, parent_id=None):
        nonlocal pos
        links = []
        for pid in paper_ids:
            valid = None
            if quote is not None:
                valid = _norm(quote) in abstracts.get(pid, "") if quote else False
            links.append({"paper_id": pid, "quote": quote, "quote_valid": valid})
        pos += 1
        return commands.apply(project_id, "ai", {
            "type": "create_board_item", "kind": kind, "text": text,
            "provenance": "ai_suggested", "status": "proposed",
            "generation_id": generation_id, "position": pos,
            "parent_id": parent_id, "papers": links,
        })["id"]

    for c in data.get("concepts", []):
        pids = resolve(c.get("papers", []))
        if pids:
            add_item("concept", c["text"], pids)
        else:
            dropped += 1

    for claim in data.get("claims", []):
        pids = resolve(claim.get("papers", []))
        if not pids:
            dropped += 1
            continue
        claim_id = add_item("claim", claim["text"], pids)
        for kind, key in (("evidence_support", "supporting"),
                          ("evidence_contradiction", "contradicting")):
            for ev in claim.get(key, []):
                ev_pids = resolve(ev.get("papers", []))
                quote = ev.get("quote", "")
                # Evidence must cite AND quote a real abstract span.
                good = [pid for pid in ev_pids if quote and _norm(quote) in abstracts.get(pid, "")]
                if good:
                    add_item(kind, ev["text"], good, quote=quote, parent_id=claim_id)
                else:
                    dropped += 1

    for q in data.get("open_questions", []):
        pids = resolve(q.get("papers", []))
        if pids:
            add_item("open_question", q["text"], pids)
        else:
            dropped += 1

    for a in data.get("next_actions", []):
        # Next actions need no citation (they're about the project, not a paper).
        add_item("next_action", a["text"], [])

    return dropped


def generate(job_id: str, project_id: str, paper_ids: list[str] | None) -> None:
    """Background entrypoint: call the model, validate, persist. Sets job state."""
    import anthropic

    conn = db.connect()
    try:
        with conn:
            conn.execute("UPDATE jobs SET status='running' WHERE id=?", (job_id,))
        project = dict(conn.execute(
            "SELECT * FROM projects WHERE id=?", (project_id,)).fetchone())
    finally:
        conn.close()

    papers = _load_papers(project_id, paper_ids)
    prompt = build_prompt(project, papers, _existing_board(project_id))
    generation_id = uuid.uuid4().hex

    client = anthropic.Anthropic()
    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=32000,
            output_config={"effort": "high",
                           "format": {"type": "json_schema", "schema": BOARD_SCHEMA}},
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            message = stream.get_final_message()
    except anthropic.APIError as e:
        with db.connect() as c, c:
            c.execute("UPDATE jobs SET status='error', error=?, finished_at=CURRENT_TIMESTAMP WHERE id=?",
                      (f"{type(e).__name__}: {e}", job_id))
        return

    text = next((b.text for b in message.content if b.type == "text"), "")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        with db.connect() as c, c:
            c.execute("UPDATE jobs SET status='error', error=?, finished_at=CURRENT_TIMESTAMP WHERE id=?",
                      (f"model returned invalid JSON: {e}", job_id))
        return

    # Clear the previous generation's still-proposed AI items (never accepted/
    # rejected/user items) only now that we have a valid replacement in hand.
    commands.apply(project_id, "ai", {"type": "delete_proposed_generation"})
    dropped = _validate_and_persist(project_id, generation_id, data, papers, job_id)
    usage = {"input_tokens": message.usage.input_tokens,
             "output_tokens": message.usage.output_tokens}
    jobs.finish_board_job(job_id, usage, dropped)
