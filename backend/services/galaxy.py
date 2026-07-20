"""Galaxy corpus access for the unified NAV app.

Lazy singleton over the ML corpus (raw papers + leiden clusters + names +
embeddings + umap) used by:
- GET /api/galaxy/search   — semantic search across the whole map
- POST /api/projects/from-cluster — seed a Research Space from a cluster

Row alignment (same assumption as pipeline + seed_demo): papers[i] (JSONL
line order) == embeddings[i] == umap[i] == leiden[i].
"""
import json
from pathlib import Path

import numpy as np

from backend import db

RAW = db.ROOT / "data" / "raw" / "arxiv_ml_subset_10k.json"
LEIDEN = db.ROOT / "data" / "clusters" / "ml_10k_leiden.json"
NAMES = db.ROOT / "data" / "clusters" / "ml_10k_names.json"
NPZ = db.ROOT / "data" / "embeddings" / "ml_10k.npz"
UMAP = db.ROOT / "data" / "projections" / "ml_10k_umap.npy"

_corpus = None


def _load():
    global _corpus
    if _corpus is not None:
        return _corpus
    papers = [json.loads(line) for line in open(RAW)]
    leiden = json.load(open(LEIDEN))
    names = json.load(open(NAMES))
    embeddings = np.load(NPZ, allow_pickle=True)["embeddings"].astype(np.float32)
    umap = np.load(UMAP).astype(np.float32)
    assert len(papers) == len(leiden) == len(embeddings) == len(umap), "corpus row mismatch"

    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    emb_norm = embeddings / norms

    # Per-cluster UMAP centroid + centrality (1 = center, 0 = edge), matching
    # the galaxy's distance-to-center definition.
    centrality = np.zeros(len(papers), dtype=np.float32)
    for cid in {c for c in leiden}:
        idx = np.array([i for i, c in enumerate(leiden) if c == cid])
        center = umap[idx].mean(axis=0)
        d = np.linalg.norm(umap[idx] - center, axis=1)
        mx = d.max() if d.max() > 0 else 1
        centrality[idx] = 1 - d / mx

    _corpus = {
        "papers": papers, "leiden": leiden, "names": names,
        "emb_norm": emb_norm, "umap": umap, "centrality": centrality,
    }
    return _corpus


def _year(p: dict) -> int | None:
    ud = p.get("update_date")
    if not ud:
        return None
    from datetime import datetime
    return datetime.fromtimestamp(ud / 1000).year


def search(query: str, k: int = 15) -> list[dict]:
    """Brute-force cosine over 10k normalized vectors — milliseconds."""
    from backend.services import embeddings as emb_svc
    c = _load()
    q = emb_svc.embed_texts([query])[0]
    scores = c["emb_norm"] @ q
    top = np.argpartition(-scores, k)[:k]
    top = top[np.argsort(-scores[top])]
    out = []
    for i in top:
        p = c["papers"][i]
        cid = c["leiden"][i]
        out.append({
            "id": p["id"],
            "title": p["title"],
            "authors": p.get("authors", ""),
            "year": _year(p),
            "abstract": (p.get("abstract") or "")[:300],
            "categories": p.get("categories", ""),
            "cluster_id": cid,
            "cluster_name": c["names"].get(str(cid), {}).get("name", ""),
            "score": float(scores[i]),
        })
    return out


def cluster_papers(cluster_id: int) -> list[dict]:
    """All papers of a cluster, most central first, with corpus row index."""
    c = _load()
    idx = [i for i, cid in enumerate(c["leiden"]) if cid == cluster_id]
    idx.sort(key=lambda i: -c["centrality"][i])
    return [{
        "row": i,
        "openalex_id": c["papers"][i]["id"],
        "doi": None,
        "title": c["papers"][i]["title"],
        "authors": c["papers"][i].get("authors"),
        "abstract": c["papers"][i].get("abstract"),
        "year": _year(c["papers"][i]),
        "venue": None,
        "cited_by_count": None,
        "pdf_url": None,
        "source": "seed",
    } for i in idx]


def cluster_name(cluster_id: int) -> str:
    return _load()["names"].get(str(cluster_id), {}).get("name", f"Cluster {cluster_id}")


def cluster_ids() -> list[int]:
    return sorted(int(k) for k in _load()["names"].keys())


def embedding_row(row: int) -> np.ndarray:
    """L2-normalized vector for a corpus row (BLOB-ready for papers.embedding)."""
    return _load()["emb_norm"][row]
