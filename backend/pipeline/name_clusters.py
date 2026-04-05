"""
Step 4: Name clusters using Claude API.
Selects papers closest to each cluster's centroid for accurate naming.
"""
import json
import numpy as np
from pathlib import Path
from sklearn.metrics.pairwise import cosine_distances
import anthropic


def get_centroid_papers(
    embeddings: np.ndarray,
    papers: list[dict],
    cluster_ids: list[int],
    cluster_id: int,
    top_k: int = 10,
) -> list[dict]:
    indices = [i for i, c in enumerate(cluster_ids) if c == cluster_id]
    if len(indices) == 0:
        return []

    cluster_embeddings = embeddings[indices]
    centroid = cluster_embeddings.mean(axis=0, keepdims=True)

    distances = cosine_distances(centroid, cluster_embeddings)[0]
    closest = np.argsort(distances)[:top_k]

    return [papers[indices[i]] for i in closest]


def name_cluster(client: anthropic.Anthropic, representative_papers: list[dict]) -> dict:
    papers_text = ""
    for i, p in enumerate(representative_papers, 1):
        abstract_preview = " ".join(p["abstract"].split()[:200])
        papers_text += f"\n{i}. Title: {p['title']}\n   Abstract: {abstract_preview}\n"

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        messages=[
            {
                "role": "user",
                "content": f"""These are the 10 most representative papers from a research cluster (closest to the cluster centroid in embedding space).

{papers_text}

Respond with ONLY a JSON object (no markdown, no explanation):
{{"name": "Short Name (2-4 words)", "description": "One sentence describing what this cluster is about."}}""",
            }
        ],
    )

    try:
        return json.loads(response.content[0].text)
    except json.JSONDecodeError:
        text = response.content[0].text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        return {"name": "Unknown Cluster", "description": "Could not parse cluster description."}


def run(
    embeddings_path: str,
    papers_path: str,
    clusters_path: str,
    output_path: str,
    min_cluster_size: int = 5,
) -> dict:
    output = Path(output_path)
    if output.exists():
        with open(output_path) as f:
            names = json.load(f)
        print(f"[name] Cache hit ({len(names)} clusters). Skipping.")
        return names

    print("[name] Loading data...")
    data = np.load(embeddings_path, allow_pickle=True)
    embeddings = data["embeddings"]

    with open(papers_path) as f:
        papers = [json.loads(line) for line in f]

    with open(clusters_path) as f:
        cluster_ids = json.load(f)

    unique_clusters = sorted(set(cluster_ids))
    cluster_sizes = {c: cluster_ids.count(c) for c in unique_clusters}

    # Filter small clusters
    valid_clusters = [c for c in unique_clusters if cluster_sizes[c] >= min_cluster_size]
    small_clusters = [c for c in unique_clusters if cluster_sizes[c] < min_cluster_size]
    small_count = sum(cluster_sizes[c] for c in small_clusters)

    print(f"[name] Naming {len(valid_clusters)} clusters ({len(small_clusters)} small clusters merged into 'Other')...")

    client = anthropic.Anthropic()
    names = {}

    for i, cluster_id in enumerate(valid_clusters):
        representative = get_centroid_papers(embeddings, papers, cluster_ids, cluster_id)
        if not representative:
            continue

        print(f"[name] Cluster {cluster_id} ({cluster_sizes[cluster_id]} papers) — {i+1}/{len(valid_clusters)}")
        result = name_cluster(client, representative)
        names[str(cluster_id)] = {
            "name": result["name"],
            "description": result["description"],
            "paper_count": cluster_sizes[cluster_id],
        }

    if small_count > 0:
        names["other"] = {
            "name": "Other Topics",
            "description": "Small clusters with fewer than 5 papers each.",
            "paper_count": small_count,
            "merged_from": small_clusters,
        }

    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(names, f, indent=2)
    print(f"[name] Saved {len(names)} cluster names to {output_path}")
    return names


if __name__ == "__main__":
    run(
        embeddings_path="data/embeddings/ml_10k.npz",
        papers_path="data/raw/arxiv_ml_subset_10k.json",
        clusters_path="data/clusters/ml_10k_leiden.json",
        output_path="data/clusters/ml_10k_names.json",
    )
