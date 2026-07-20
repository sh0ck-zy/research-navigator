"""
Orchestrates the full pipeline: data → embeddings → UMAP → clusters → names → export.

Usage:
    python run_pipeline.py                # default field: ml
    python run_pipeline.py --field neuro  # Rabanadas corpus
"""
import argparse
import json
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


# Each field defines its OpenAlex concept filter and a slug used in all data paths.
FIELDS = {
    "ml": {
        "name": "Machine Learning",
        "slug": "ml_10k",
        "raw_file": "arxiv_ml_subset_10k.json",  # legacy filename, keep cache valid
        "concept_ids": ["C119857082"],
    },
    "neuro": {
        "name": "Functional Neuroimaging",
        "slug": "neuro_10k",
        "raw_file": "neuro_10k.jsonl",
        # fMRI, Functional connectivity, Functional neuroimaging, Connectome
        "concept_ids": ["C2779226451", "C3018011982", "C52338299", "C45715564"],
    },
}


def field_paths(field: dict) -> dict:
    slug = field["slug"]
    return {
        "data": str(ROOT / "data" / "raw" / field["raw_file"]),
        "embeddings": str(ROOT / "data" / "embeddings" / f"{slug}.npz"),
        "projections": str(ROOT / "data" / "projections" / f"{slug}_umap.npy"),
        "clusters": str(ROOT / "data" / "clusters" / f"{slug}_leiden.json"),
        "names": str(ROOT / "data" / "clusters" / f"{slug}_names.json"),
        "export": str(ROOT / "galaxy" / "data" / "map_data.json"),
    }


def write_active_field(field: dict, paths: dict):
    """Record which corpus is live so api.py serves search over the same data."""
    active = {
        "field": field["name"],
        "slug": field["slug"],
        "raw_file": field["raw_file"],  # basename — api.py derives full paths from slug
        "papers_path": paths["data"],
        "embeddings_path": paths["embeddings"],
        "clusters_path": paths["clusters"],
        "names_path": paths["names"],
    }
    with open(ROOT / "data" / "active_field.json", "w") as f:
        json.dump(active, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Run the Clarity pipeline for a field")
    parser.add_argument("--field", choices=FIELDS.keys(), default="ml")
    parser.add_argument("--count", type=int, default=10000)
    parser.add_argument("--skip-naming", action="store_true",
                        help="Skip Claude naming (names file must already exist)")
    args = parser.parse_args()

    field = FIELDS[args.field]
    paths = field_paths(field)

    start = time.time()
    print("=" * 60)
    print("  Clarity Research — Pipeline")
    print(f"  Field: {field['name']}")
    print("  Researchers fly blind. We give them the map.")
    print("=" * 60)
    print()

    # Step 0: Ingest (skips if data exists)
    run_ingest(paths["data"], target_count=args.count, concept_ids=field["concept_ids"])
    print()

    # Step 1: Embeddings
    run_embed(paths["data"], paths["embeddings"])
    print()

    # Step 2: UMAP projection
    run_project(paths["embeddings"], paths["projections"])
    print()

    # Step 3: Leiden clustering
    run_cluster(paths["embeddings"], paths["clusters"])
    print()

    # Step 4: Name clusters with Claude
    if not args.skip_naming:
        run_name(paths["embeddings"], paths["data"], paths["clusters"], paths["names"])
        print()

    # Step 5: Export for galaxy
    run_export(paths["data"], paths["projections"], paths["clusters"], paths["names"],
               paths["embeddings"], paths["export"], field_name=field["name"])
    print()

    write_active_field(field, paths)

    elapsed = time.time() - start
    print("=" * 60)
    print(f"  Done in {elapsed:.1f}s")
    print(f"  Serve with: uvicorn backend.api:app --port 8000")
    print("=" * 60)


if __name__ == "__main__":
    main()
