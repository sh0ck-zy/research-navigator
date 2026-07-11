"""Seed a demo project from the neuro corpus — no network, no model load.

Filters ~60 explainable-AI-for-fMRI papers out of data/raw/neuro_10k.jsonl,
copies their precomputed MiniLM vectors from the .npz (line order == row
order, the same assumption api.py relies on), and builds a project through
commands.apply so the event log and provenance are real.

    python -m backend.scripts.seed_demo [--reset]

Vectors in the .npz are raw (embed.py doesn't normalize); we L2-normalize on
copy so they match freshly enriched papers, which store normalized vectors.
"""
import argparse
import json
import uuid

import numpy as np

from backend import db
from backend.services import commands

RAW = db.ROOT / "data" / "raw" / "neuro_10k.jsonl"
NPZ = db.ROOT / "data" / "embeddings" / "neuro_10k.npz"

PROJECT = {
    "name": "Explainable AI methods for fMRI analysis",
    "research_question": (
        "Can explainability methods make deep-learning models trained on fMRI "
        "functional connectivity trustworthy enough for clinical diagnosis?"
    ),
    "hypothesis": (
        "Saliency and attention over connectivity graphs surface diagnostically "
        "meaningful regions rather than dataset artifacts."
    ),
    "scope_notes": "Deep learning on fMRI/functional connectivity; interpretability, saliency, GNNs, transformers.",
}

# A paper is in-scope if it mentions a method term AND an fMRI/brain term.
METHOD = ("interpretab", "explainab", "saliency", "attention", "feature importance",
          "deep learning", "graph neural", "neural network", "convolutional")
DOMAIN = ("fmri", "functional connectivity", "functional mri", "connectome",
          "resting-state", "resting state", "brain network")
MAX_PAPERS = 60


def _in_scope(text: str) -> bool:
    t = text.lower()
    return any(m in t for m in METHOD) and any(d in t for d in DOMAIN)


def main(reset: bool) -> None:
    db.migrate()
    papers = [json.loads(line) for line in open(RAW)]
    embeddings = np.load(NPZ, allow_pickle=True)["embeddings"].astype(np.float32)
    assert len(papers) == len(embeddings), "row/line mismatch"

    picked = [(i, p) for i, p in enumerate(papers)
              if _in_scope(f"{p['title']} {p.get('abstract', '')}")][:MAX_PAPERS]
    if not picked:
        print("[seed] no papers matched the filter")
        return

    with db.connect() as conn:
        if reset:
            conn.execute("DELETE FROM projects WHERE name = ?", (PROJECT["name"],))

    project_id = uuid.uuid4().hex
    commands.apply(project_id, "user", {"type": "create_project", **PROJECT})

    rows = [{
        "openalex_id": p["id"],
        "doi": p.get("doi") or None,
        "title": p["title"],
        "authors": p.get("authors"),
        "abstract": p.get("abstract"),
        "year": p.get("year"),
        "venue": p.get("venue") or None,
        "cited_by_count": p.get("cited_by_count"),
        "source": "seed",
    } for _, p in picked]
    result = commands.apply(project_id, "user", {"type": "add_papers", "papers": rows})

    # Map inserted ids back to their corpus row to copy the right vector.
    with db.connect() as conn:
        db_rows = conn.execute(
            "SELECT id, openalex_id FROM papers WHERE project_id = ?", (project_id,)
        ).fetchall()
    oa_to_row = {p["id"]: idx for idx, p in picked}
    for r in db_rows:
        idx = oa_to_row.get(r["openalex_id"])
        if idx is None:
            continue
        vec = embeddings[idx]
        norm = np.linalg.norm(vec)
        vec = (vec / norm) if norm else vec
        commands.apply(project_id, "ai", {
            "type": "update_paper", "paper_id": r["id"],
            "embedding": vec.astype(np.float32).tobytes(),
            "enrichment_status": "enriched",
        })

    print(f"[seed] project {project_id}")
    print(f"[seed] {len(result['inserted'])} papers seeded ({len(picked)} matched, {MAX_PAPERS} cap)")
    print(f"[seed] open: http://localhost:8000/projects/{project_id}/library")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="delete an existing demo project first")
    main(ap.parse_args().reset)
