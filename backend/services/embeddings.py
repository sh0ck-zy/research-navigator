"""Per-project embeddings + search.

Same model as the galaxy corpus (all-MiniLM-L6-v2) and the same
"title. abstract" composition as pipeline/embed.py, so seed-script vectors
copied from the precomputed .npz are compatible with freshly encoded ones.

At 20-300 papers a brute-force numpy dot product is microseconds — no FAISS,
no index lifecycle. Vectors live as float32 BLOBs on the papers table.
"""
import numpy as np

from backend import db

MODEL_NAME = "all-MiniLM-L6-v2"
DIM = 384

_model = None


def _get_model():
    """Lazy singleton — importing this module must not load the model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def compose(title: str, abstract: str | None) -> str:
    title = (title or "").strip()
    abstract = (abstract or "").strip()
    return f"{title}. {abstract}".strip() if abstract else title


def embed_texts(texts: list[str]) -> np.ndarray:
    """L2-normalized float32 embeddings, shape (n, DIM)."""
    vecs = _get_model().encode(
        texts, normalize_embeddings=True, batch_size=64, show_progress_bar=False
    )
    return np.asarray(vecs, dtype=np.float32)


def to_blob(vec: np.ndarray) -> bytes:
    return np.asarray(vec, dtype=np.float32).tobytes()


def from_blob(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def semantic_search(project_id: str, query: str, k: int = 15) -> list[tuple[str, float]]:
    """Return [(paper_id, cosine_score)] top-k within the project."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT id, embedding FROM papers WHERE project_id = ? AND embedding IS NOT NULL",
            (project_id,),
        ).fetchall()
    if not rows:
        return []
    ids = [r["id"] for r in rows]
    matrix = np.stack([from_blob(r["embedding"]) for r in rows])  # (n, DIM), already normalized
    qvec = embed_texts([query])[0]
    scores = matrix @ qvec
    top = np.argsort(-scores)[:k]
    return [(ids[i], round(float(scores[i]), 4)) for i in top]
