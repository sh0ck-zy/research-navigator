"""
Step 0: Fetch ~10k ML papers from OpenAlex API.

OpenAlex is a free, open catalog of the world's scholarly works.
We query for Machine Learning papers (concept C119857082) and extract
title, abstract, authors, year, and citation count.

Usage:
    python ingest.py                     # fetch ~10k ML papers
    python ingest.py --count 5000        # fetch ~5k papers
    python ingest.py --query "robotics"  # search for robotics papers
"""
import json
import argparse
import time
from pathlib import Path

import requests
from tqdm import tqdm


OPENALEX_WORKS = "https://api.openalex.org/works"
ML_CONCEPT_ID = "C119857082"
USER_AGENT = "ClarityResearch/0.1 (mailto:clarity@example.com)"


def reconstruct_abstract(inverted_index: dict) -> str:
    """Reconstruct abstract text from OpenAlex inverted index format."""
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort()
    return " ".join(word for _, word in word_positions)


def fetch_papers(
    concept_id: str = ML_CONCEPT_ID,
    query: str | None = None,
    target_count: int = 10000,
    per_page: int = 200,
) -> list[dict]:
    """Fetch papers from OpenAlex API with cursor pagination."""
    papers = []
    cursor = "*"
    headers = {"User-Agent": USER_AGENT}

    params = {
        "per_page": per_page,
        "sort": "cited_by_count:desc",
        "select": "id,title,publication_year,cited_by_count,authorships,concepts,abstract_inverted_index",
    }

    if query:
        params["search"] = query
    else:
        params["filter"] = f"concepts.id:{concept_id},type:article,has_abstract:true"

    pbar = tqdm(total=target_count, desc="Fetching papers")

    while len(papers) < target_count:
        params["cursor"] = cursor
        try:
            resp = requests.get(OPENALEX_WORKS, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"\n[ingest] API error: {e}. Retrying in 5s...")
            time.sleep(5)
            continue

        results = data.get("results", [])
        if not results:
            break

        for work in results:
            authors = ", ".join(
                a["author"]["display_name"]
                for a in (work.get("authorships") or [])
                if a.get("author", {}).get("display_name")
            )

            abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
            if not abstract:
                continue

            categories = " ".join(
                c["display_name"]
                for c in (work.get("concepts") or [])[:5]
                if c.get("display_name")
            )

            papers.append({
                "id": work.get("id", "").replace("https://openalex.org/", ""),
                "title": work.get("title", "Untitled"),
                "authors": authors,
                "abstract": abstract,
                "year": work.get("publication_year"),
                "cited_by_count": work.get("cited_by_count", 0),
                "categories": categories,
            })

        cursor = data.get("meta", {}).get("next_cursor")
        if not cursor:
            break

        pbar.update(len(results))
        time.sleep(0.1)  # Be polite to the API

    pbar.close()
    return papers[:target_count]


def run(output_path: str, target_count: int = 10000, query: str | None = None):
    output = Path(output_path)
    if output.exists():
        line_count = sum(1 for _ in open(output_path))
        print(f"[ingest] Data already exists ({line_count} papers). Skipping.")
        print(f"[ingest] Delete {output_path} to re-fetch.")
        return

    print(f"[ingest] Fetching ~{target_count} papers from OpenAlex...")
    papers = fetch_papers(target_count=target_count, query=query)

    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        for paper in papers:
            f.write(json.dumps(paper) + "\n")

    print(f"[ingest] Saved {len(papers)} papers to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch ML papers from OpenAlex")
    parser.add_argument("--count", type=int, default=10000, help="Number of papers to fetch")
    parser.add_argument("--query", type=str, default=None, help="Search query (instead of ML concept)")
    parser.add_argument("--output", type=str, default="data/raw/papers.jsonl", help="Output path")
    args = parser.parse_args()

    run(output_path=args.output, target_count=args.count, query=args.query)
