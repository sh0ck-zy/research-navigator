"""Export a project's library (.bib) and board (.md)."""
from contextlib import closing

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from backend import db
from backend.citations import bibtex_for_many

router = APIRouter(prefix="/api/projects/{project_id}/export", tags=["export"])

DISCLAIMER = (
    "> Drafted from titles and abstracts only — verify against the full text "
    "before relying on any claim.\n"
)


def _project_or_404(conn, project_id):
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row is None:
        raise HTTPException(404, f"project {project_id} not found")
    return dict(row)


def _slug(name: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-") or "project"


@router.get(".bib")
def export_bib(project_id: str):
    with closing(db.connect()) as conn:
        project = _project_or_404(conn, project_id)
        rows = conn.execute(
            """SELECT openalex_id AS id, title, authors, year, doi, venue
               FROM papers WHERE project_id = ? ORDER BY cited_by_count DESC NULLS LAST""",
            (project_id,),
        ).fetchall()
    bib = bibtex_for_many([dict(r) for r in rows])
    return Response(
        content=bib, media_type="text/x-bibtex",
        headers={"Content-Disposition": f'attachment; filename="{_slug(project["name"])}.bib"'},
    )


def _cite(papers: list[dict]) -> str:
    """Inline citation: [Author Year](doi) chips."""
    out = []
    for p in papers:
        first = (p["authors"] or "").split(",")[0].strip() or "—"
        label = f"{first} {p['year']}" if p["year"] else first
        out.append(f"[{label}](https://doi.org/{p['doi']})" if p["doi"] else label)
    return " ".join(out)


@router.get(".md")
def export_md(project_id: str):
    with closing(db.connect()) as conn:
        project = _project_or_404(conn, project_id)
        # The curated board: accepted or user-authored items only.
        items = [dict(r) for r in conn.execute(
            """SELECT * FROM board_items WHERE project_id = ?
               AND (status = 'accepted' OR provenance IN ('user_created','user_edited'))
               ORDER BY position, created_at""",
            (project_id,),
        ).fetchall()]
        links = conn.execute(
            """SELECT bip.item_id, p.authors, p.year, p.doi, bip.quote
               FROM board_item_papers bip JOIN papers p ON p.id = bip.paper_id
               WHERE p.project_id = ?""",
            (project_id,),
        ).fetchall()

    papers_by_item: dict[str, list] = {}
    for l in links:
        papers_by_item.setdefault(l["item_id"], []).append(dict(l))
    for it in items:
        it["papers"] = papers_by_item.get(it["id"], [])

    def of(kind, parent=None):
        return [i for i in items if i["kind"] == kind and i["parent_id"] == parent]

    def bullet(item) -> str:
        cite = _cite(item["papers"])
        return f"- {item['text']} — {cite}" if cite else f"- {item['text']}"

    md = [f"# {project['name']}", "", DISCLAIMER, "",
          f"**Research question:** {project['research_question']}", ""]
    if project.get("hypothesis"):
        md += [f"**Working hypothesis:** {project['hypothesis']}", ""]

    concepts = of("concept")
    if concepts:
        md += ["## Central concepts", ""]
        md += [bullet(c) for c in concepts] + [""]

    claims = of("claim")
    if claims:
        md += ["## Claims", ""]
        for c in claims:
            md.append(f"### {c['text']}")
            md.append(f"_{_cite(c['papers'])}_" if c["papers"] else "")
            for ev in of("evidence_support", c["id"]):
                md.append(f"- ✅ {ev['text']} — {_cite(ev['papers'])}")
            for ev in of("evidence_contradiction", c["id"]):
                md.append(f"- ⚠️ {ev['text']} — {_cite(ev['papers'])}")
            md.append("")

    questions = of("open_question")
    if questions:
        md += ["## Open questions", ""]
        md += [bullet(q) for q in questions] + [""]

    actions = of("next_action")
    if actions:
        md += ["## Next actions", ""]
        md += [f"- [ ] {a['text']}" for a in actions] + [""]

    return Response(
        content="\n".join(md), media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{_slug(project["name"])}-board.md"'},
    )
