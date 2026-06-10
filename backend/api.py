"""
Clarity Research API — semantic search over 10k ML papers.
Uses FAISS for vector similarity and SentenceTransformers for query encoding.
"""
import json
import os
from pathlib import Path

import faiss
import numpy as np
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sentence_transformers import SentenceTransformer

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
FRONTEND_DIR = ROOT / "frontend"

# The pipeline records which corpus is live in data/active_field.json;
# fall back to the original ML corpus if it doesn't exist.
ACTIVE_FIELD_PATH = DATA_DIR / "active_field.json"
if ACTIVE_FIELD_PATH.exists():
    with open(ACTIVE_FIELD_PATH) as f:
        _active = json.load(f)
    EMBEDDINGS_PATH = Path(_active["embeddings_path"])
    PAPERS_PATH = Path(_active["papers_path"])
    CLUSTERS_PATH = Path(_active["clusters_path"])
    NAMES_PATH = Path(_active["names_path"])
else:
    EMBEDDINGS_PATH = DATA_DIR / "embeddings" / "ml_10k.npz"
    PAPERS_PATH = DATA_DIR / "raw" / "arxiv_ml_subset_10k.json"
    CLUSTERS_PATH = DATA_DIR / "clusters" / "ml_10k_leiden.json"
    NAMES_PATH = DATA_DIR / "clusters" / "ml_10k_names.json"

# ── Load data at startup ─────────────────────────────────────────────────────
print("[api] Loading data...")

# Papers
with open(PAPERS_PATH) as f:
    papers = [json.loads(line) for line in f]

# Cluster assignments
with open(CLUSTERS_PATH) as f:
    cluster_ids = json.load(f)

# Cluster names
with open(NAMES_PATH) as f:
    cluster_names = json.load(f)

# Build cluster lookup: paper index → {name, id}
# Handle "other" merged clusters
other_ids = set()
if "other" in cluster_names and "merged_from" in cluster_names["other"]:
    other_ids = set(cluster_names["other"]["merged_from"])

paper_cluster_info = []
for i, cid in enumerate(cluster_ids):
    effective_cid = "other" if cid in other_ids else str(cid)
    info = cluster_names.get(effective_cid, {"name": "Other", "description": ""})
    paper_cluster_info.append({
        "cluster_id": effective_cid,
        "cluster_name": info["name"],
    })

# Embeddings + FAISS index
data = np.load(EMBEDDINGS_PATH, allow_pickle=True)
embeddings = data["embeddings"].astype(np.float32)

# Normalize for cosine similarity (FAISS inner product on normalized = cosine)
faiss.normalize_L2(embeddings)
index = faiss.IndexFlatIP(embeddings.shape[1])
index.add(embeddings)

# Encoder model (same one used to generate embeddings)
print("[api] Loading SentenceTransformer model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

print(f"[api] Ready — {len(papers)} papers, {embeddings.shape[1]}-dim, FAISS index built.")

# ── FastAPI app ──────────────────────────────────────────────────────────────
app = FastAPI(title="Clarity Research API")


@app.get("/api/search")
def search(
    q: str = Query(..., min_length=1, max_length=500),
    k: int = Query(15, ge=1, le=50),
):
    """Semantic search: encode query, find nearest papers via FAISS."""
    # Encode query
    query_vec = model.encode([q], normalize_embeddings=True).astype(np.float32)

    # Search
    scores, indices = index.search(query_vec, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        p = papers[idx]
        ci = paper_cluster_info[idx]
        results.append({
            "id": p.get("id", str(idx)),
            "title": p.get("title", "Untitled"),
            "authors": p.get("authors", ""),
            "year": p.get("year"),
            "abstract": p.get("abstract", "")[:300],
            "categories": p.get("categories", ""),
            "cluster_name": ci["cluster_name"],
            "cluster_id": ci["cluster_id"],
            "score": round(float(score), 4),
            "index": int(idx),
        })

    return {"query": q, "results": results}


# ── Serve frontend ───────────────────────────────────────────────────────────
# Production serves the Vite build (frontend/dist); during development run
# `npm run dev` in frontend/ instead (it proxies /api here and serves data/ itself).
DIST_DIR = FRONTEND_DIR / "dist"
SERVE_DIR = DIST_DIR if DIST_DIR.exists() else FRONTEND_DIR


@app.get("/")
def serve_index():
    return FileResponse(SERVE_DIR / "index.html")


app.mount("/data", StaticFiles(directory=FRONTEND_DIR / "data"), name="data")
app.mount("/", StaticFiles(directory=SERVE_DIR), name="static")
