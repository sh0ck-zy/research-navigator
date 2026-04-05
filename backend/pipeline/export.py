"""
Step 5: Export all processed data into a single JSON for the frontend.
"""
import json
import numpy as np
from pathlib import Path
from collections import defaultdict
from datetime import date

# 20 distinct colors for clusters
PALETTE = [
    "#4A9EFF", "#FF6B8A", "#8B5CF6", "#F59E0B", "#10B981",
    "#06B6D4", "#EC4899", "#84CC16", "#F97316", "#6366F1",
    "#14B8A6", "#E11D48", "#A855F7", "#EAB308", "#22D3EE",
    "#FB7185", "#34D399", "#FBBF24", "#818CF8", "#2DD4BF",
]


def compute_connections(
    embeddings: np.ndarray,
    cluster_ids: list[int],
    knn_indices: np.ndarray,
) -> list[dict]:
    """Compute inter-cluster connections based on cross-cluster kNN edges."""
    cross_counts = defaultdict(int)
    total_counts = defaultdict(int)

    for i, neighbors in enumerate(knn_indices):
        ci = cluster_ids[i]
        total_counts[ci] += len(neighbors)
        for j in neighbors:
            cj = cluster_ids[j]
            if ci != cj:
                key = (min(ci, cj), max(ci, cj))
                cross_counts[key] += 1

    connections = []
    for (c1, c2), count in cross_counts.items():
        total = total_counts[c1] + total_counts[c2]
        strength = round(count / total, 4) if total > 0 else 0
        if strength > 0.01:
            connections.append({"from": c1, "to": c2, "strength": strength})

    connections.sort(key=lambda x: x["strength"], reverse=True)
    return connections


def run(
    papers_path: str,
    coords_path: str,
    clusters_path: str,
    names_path: str,
    embeddings_path: str,
    output_path: str,
):
    print("[export] Loading all data...")

    with open(papers_path) as f:
        papers = [json.loads(line) for line in f]

    coords = np.load(coords_path)

    with open(clusters_path) as f:
        cluster_ids = json.load(f)

    with open(names_path) as f:
        cluster_names = json.load(f)

    data = np.load(embeddings_path, allow_pickle=True)
    embeddings = data["embeddings"]

    # Normalize coordinates to [0, 1]
    x_min, x_max = coords[:, 0].min(), coords[:, 0].max()
    y_min, y_max = coords[:, 1].min(), coords[:, 1].max()
    norm_x = (coords[:, 0] - x_min) / (x_max - x_min)
    norm_y = (coords[:, 1] - y_min) / (y_max - y_min)

    # Add padding (5% on each side)
    norm_x = 0.05 + norm_x * 0.9
    norm_y = 0.05 + norm_y * 0.9

    # Build kNN for connections
    from sklearn.neighbors import NearestNeighbors
    nn = NearestNeighbors(n_neighbors=15, metric="cosine")
    nn.fit(embeddings)
    _, knn_indices = nn.kneighbors(embeddings)

    connections = compute_connections(embeddings, cluster_ids, knn_indices)

    # Handle "other" cluster merging
    other_ids = set()
    if "other" in cluster_names and "merged_from" in cluster_names["other"]:
        other_ids = set(cluster_names["other"]["merged_from"])

    # Group papers by cluster
    clusters_data = defaultdict(list)
    for i, paper in enumerate(papers):
        cid = cluster_ids[i]
        effective_cid = "other" if cid in other_ids else str(cid)

        year = None
        if "update_date" in paper and paper["update_date"]:
            try:
                from datetime import datetime
                ud = paper["update_date"]
                if isinstance(ud, (int, float)) and ud > 1e12:
                    year = datetime.fromtimestamp(ud / 1000).year
                elif isinstance(ud, (int, float)) and ud > 1e9:
                    year = datetime.fromtimestamp(ud).year
                elif isinstance(ud, str) and len(ud) >= 4:
                    year = int(ud[:4])
            except (ValueError, TypeError, OSError):
                pass

        clusters_data[effective_cid].append({
            "id": paper.get("id", str(i)),
            "title": paper.get("title", "Untitled"),
            "authors": paper.get("authors", ""),
            "year": year,
            "abstract": paper.get("abstract", "")[:500],
            "x": round(float(norm_x[i]), 5),
            "y": round(float(norm_y[i]), 5),
            "categories": paper.get("categories", ""),
        })

    # Build cluster objects
    clusters_output = []
    for idx, (cid, info) in enumerate(cluster_names.items()):
        if cid not in clusters_data:
            continue

        papers_in_cluster = clusters_data[cid]
        center_x = round(np.mean([p["x"] for p in papers_in_cluster]), 5)
        center_y = round(np.mean([p["y"] for p in papers_in_cluster]), 5)

        clusters_output.append({
            "id": int(cid) if cid != "other" else -1,
            "name": info["name"],
            "description": info["description"],
            "paper_count": len(papers_in_cluster),
            "center_x": center_x,
            "center_y": center_y,
            "color": PALETTE[idx % len(PALETTE)],
            "papers": papers_in_cluster,
        })

    # Sort by paper count descending
    clusters_output.sort(key=lambda c: c["paper_count"], reverse=True)

    output = {
        "metadata": {
            "field": "Machine Learning",
            "paper_count": len(papers),
            "cluster_count": len(clusters_output),
            "generated_at": str(date.today()),
        },
        "clusters": clusters_output,
        "connections": connections[:50],  # Top 50 connections
    }

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f)

    size_mb = output_file.stat().st_size / (1024 * 1024)
    print(f"[export] Saved {output_path} — {len(clusters_output)} clusters, {len(papers)} papers, {size_mb:.1f}MB")


if __name__ == "__main__":
    run(
        papers_path="data/raw/arxiv_ml_subset_10k.json",
        coords_path="data/projections/ml_10k_umap.npy",
        clusters_path="data/clusters/ml_10k_leiden.json",
        names_path="data/clusters/ml_10k_names.json",
        embeddings_path="data/embeddings/ml_10k.npz",
        output_path="frontend/data/map_data.json",
    )
