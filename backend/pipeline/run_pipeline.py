"""
Orchestrates the full pipeline: data → embeddings → UMAP → clusters → names → export.
"""
import sys
import time
from pathlib import Path

# Ensure we run from repo root
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "backend" / "pipeline"))

from ingest import run as run_ingest
from embed import run as run_embed
from project import run as run_project
from cluster import run as run_cluster
from name_clusters import run as run_name
from export import run as run_export


def main():
    start = time.time()
    print("=" * 60)
    print("  Clarity Research — Pipeline")
    print("  Researchers fly blind. We give them the map.")
    print("=" * 60)
    print()

    data_path = str(ROOT / "data" / "raw" / "arxiv_ml_subset_10k.json")
    embeddings_path = str(ROOT / "data" / "embeddings" / "ml_10k.npz")
    projections_path = str(ROOT / "data" / "projections" / "ml_10k_umap.npy")
    clusters_path = str(ROOT / "data" / "clusters" / "ml_10k_leiden.json")
    names_path = str(ROOT / "data" / "clusters" / "ml_10k_names.json")
    export_path = str(ROOT / "frontend" / "data" / "map_data.json")

    # Step 0: Ingest (skips if data exists)
    run_ingest(data_path)
    print()

    # Step 1: Embeddings
    run_embed(data_path, embeddings_path)
    print()

    # Step 2: UMAP projection
    run_project(embeddings_path, projections_path)
    print()

    # Step 3: Leiden clustering
    run_cluster(embeddings_path, clusters_path)
    print()

    # Step 4: Name clusters with Claude
    run_name(embeddings_path, data_path, clusters_path, names_path)
    print()

    # Step 5: Export for frontend
    run_export(data_path, projections_path, clusters_path, names_path, embeddings_path, export_path)
    print()

    elapsed = time.time() - start
    print("=" * 60)
    print(f"  Done in {elapsed:.1f}s")
    print(f"  Open frontend/index.html in your browser.")
    print("=" * 60)


if __name__ == "__main__":
    main()
