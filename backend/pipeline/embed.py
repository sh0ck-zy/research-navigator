"""
Step 1: Generate embeddings for paper abstracts.
Reuses logic from research-papers-network/embedding_generator.py
"""
import json
import hashlib
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer


def get_texts_hash(texts: list[str]) -> str:
    combined = "".join(texts)
    return hashlib.md5(combined.encode()).hexdigest()


def generate_embeddings(
    texts: list[str],
    model_name: str = "all-MiniLM-L6-v2",
) -> np.ndarray:
    model = SentenceTransformer(model_name)
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=64)
    return np.array(embeddings)


def run(data_path: str, output_path: str) -> np.ndarray:
    print("[embed] Loading papers...")
    with open(data_path, "r") as f:
        papers = [json.loads(line) for line in f]

    texts = [f"{p['title']}. {p['abstract']}" for p in papers]
    texts_hash = get_texts_hash(texts)

    output = Path(output_path)
    if output.exists():
        cached = np.load(output_path, allow_pickle=True)
        if cached.get("hash", None) is not None and str(cached["hash"]) == texts_hash:
            print(f"[embed] Cache hit ({len(texts)} papers). Skipping.")
            return cached["embeddings"]

    print(f"[embed] Generating embeddings for {len(texts)} papers...")
    embeddings = generate_embeddings(texts)

    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_path, embeddings=embeddings, hash=texts_hash)
    print(f"[embed] Saved to {output_path} — shape {embeddings.shape}")
    return embeddings


if __name__ == "__main__":
    run(
        data_path="data/raw/arxiv_ml_subset_10k.json",
        output_path="data/embeddings/ml_10k.npz",
    )
