"""
Step 3: Detect communities using Leiden algorithm.
"""
import json
import numpy as np
from pathlib import Path
from sklearn.neighbors import NearestNeighbors
import igraph as ig
import leidenalg


def build_knn_graph(embeddings: np.ndarray, k: int = 15) -> ig.Graph:
    print(f"[cluster] Building kNN graph (k={k})...")
    nn = NearestNeighbors(n_neighbors=k, metric="cosine")
    nn.fit(embeddings)
    distances, indices = nn.kneighbors(embeddings)

    edges = set()
    for i, neighbors in enumerate(indices):
        for j in neighbors:
            if i != j:
                edge = (min(i, j), max(i, j))
                edges.add(edge)

    g = ig.Graph(n=len(embeddings), edges=list(edges), directed=False)
    return g


def run(embeddings_path: str, output_path: str) -> list[int]:
    output = Path(output_path)
    if output.exists():
        with open(output_path) as f:
            clusters = json.load(f)
        print(f"[cluster] Cache hit ({len(clusters)} papers). Skipping.")
        return clusters

    print("[cluster] Loading embeddings...")
    data = np.load(embeddings_path, allow_pickle=True)
    embeddings = data["embeddings"]

    graph = build_knn_graph(embeddings, k=15)

    print("[cluster] Running Leiden algorithm...")
    partition = leidenalg.find_partition(graph, leidenalg.ModularityVertexPartition)
    clusters = list(partition.membership)

    n_clusters = len(set(clusters))
    print(f"[cluster] Found {n_clusters} communities")

    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(clusters, f)
    print(f"[cluster] Saved to {output_path}")
    return clusters


if __name__ == "__main__":
    run(
        embeddings_path="data/embeddings/ml_10k.npz",
        output_path="data/clusters/ml_10k_leiden.json",
    )
