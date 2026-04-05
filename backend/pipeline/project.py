"""
Step 2: Project embeddings to 2D using UMAP.
"""
import numpy as np
from pathlib import Path
from umap import UMAP


def run(embeddings_path: str, output_path: str) -> np.ndarray:
    print("[project] Loading embeddings...")
    data = np.load(embeddings_path, allow_pickle=True)
    embeddings = data["embeddings"]

    output = Path(output_path)
    if output.exists():
        coords = np.load(output_path)
        if coords.shape[0] == embeddings.shape[0]:
            print(f"[project] Cache hit ({coords.shape[0]} papers). Skipping.")
            return coords

    print(f"[project] Running UMAP on {embeddings.shape[0]} papers...")
    reducer = UMAP(
        n_neighbors=15,
        min_dist=0.1,
        n_components=2,
        metric="cosine",
        random_state=42,
    )
    coords = reducer.fit_transform(embeddings)

    output.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, coords)
    print(f"[project] Saved to {output_path} — shape {coords.shape}")
    return coords


if __name__ == "__main__":
    run(
        embeddings_path="data/embeddings/ml_10k.npz",
        output_path="data/projections/ml_10k_umap.npy",
    )
