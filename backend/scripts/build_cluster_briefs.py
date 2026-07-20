"""Build cluster briefs for the ML galaxy — structural intelligence, no LLM.

Generates frontend/data/cluster_briefs.json, consumed by the Cluster
Intelligence Page (frontend/src/intel.js). Everything here is computed from
the corpus: sub-areas (k-means over embeddings, labelled by distinctive
title terms), movement trends (per-year rates), king papers (UMAP
centrality). Schools/debates/open_questions are null — they wait for the
LLM analyst pass (ADR-011 v0.1).

    python -m backend.scripts.build_cluster_briefs
"""
import json
import re
from collections import Counter

import numpy as np

from backend import db
from backend.services import galaxy

OUT = db.ROOT / "frontend" / "data" / "cluster_briefs.json"

STOP = set("""
the a an and or of in on for to with from by at as is are was were be been
we our this that these those it its their his her they them he she you your
via using use used based new towards between over under into upon within
without across show shows shown propose proposed present presented study
method methods approach approaches model models framework task tasks problem
problems result results experiment experiments analysis performance data
""".split())

TOKEN_RE = re.compile(r"[a-z][a-z\-]{2,}")


def _tokens(title: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(title.lower()) if t not in STOP]


def _kmeans(vecs: np.ndarray, k: int, seed: int, iters: int = 30) -> np.ndarray:
    rng = np.random.default_rng(seed)
    centroids = [vecs[rng.integers(len(vecs))]]
    for _ in range(k - 1):
        d = np.minimum.reduce([np.sum((vecs - c) ** 2, axis=1) for c in centroids])
        probs = d / d.sum() if d.sum() > 0 else np.full(len(vecs), 1 / len(vecs))
        centroids.append(vecs[rng.choice(len(vecs), p=probs)])
    centroids = np.array(centroids)
    assign = np.zeros(len(vecs), dtype=int)
    for _ in range(iters):
        dists = np.sum((vecs[:, None, :] - centroids[None, :, :]) ** 2, axis=2)
        new = dists.argmin(axis=1)
        if (new == assign).all():
            break
        assign = new
        for j in range(k):
            members = vecs[assign == j]
            if len(members):
                centroids[j] = members.mean(axis=0)
    return assign


def _label(member_titles: list[str], cluster_counts: Counter) -> tuple[str, list[str]]:
    uni, bi = Counter(), Counter()
    for t in member_titles:
        toks = _tokens(t)
        uni.update(toks)
        bi.update(zip(toks, toks[1:]))

    def score(count, key):
        return (count + 0.5) / (cluster_counts.get(key, 0) + 1)

    cands = [(" ".join(k), score(c, k)) for k, c in bi.items() if c >= 2]
    cands += [(k, score(c, k) * 0.7) for k, c in uni.items() if c >= 2]
    cands.sort(key=lambda x: -x[1])
    top = [w for w, _ in cands[:3]]
    return (" / ".join(top[:2]) if top else "misc", top)


def build() -> dict:
    c = galaxy._load()
    papers, leiden, names = c["papers"], c["leiden"], c["names"]
    emb, umap, centrality = c["emb_norm"], c["umap"], c["centrality"]
    years = np.array([galaxy._year(p) or 0 for p in papers])
    max_year = int(years.max())

    briefs = {}
    for cid in galaxy.cluster_ids():
        idx = np.array([i for i, x in enumerate(leiden) if x == cid])
        n = len(idx)
        cy = years[idx]
        valid = cy[cy > 0]
        hist = {int(y): int((cy == y).sum()) for y in sorted(set(cy)) if y > 0}

        recent = int((cy >= max_year - 1).sum())
        prior = int(((cy >= max_year - 3) & (cy < max_year - 1)).sum())
        growth = (recent / 2) / (prior / 2) - 1 if prior else None

        order = idx[np.argsort(-centrality[idx])]
        kings = [{
            "id": papers[i]["id"], "title": papers[i]["title"],
            "authors": papers[i].get("authors", ""), "year": int(years[i]) or None,
        } for i in order[:5]]

        center = umap[idx].mean(axis=0)
        radius = np.percentile(np.linalg.norm(umap[idx] - center, axis=1), 90) or 1

        k = max(1, min(5, round(n / 150)))
        cluster_counts = Counter()
        for i in idx:
            toks = _tokens(papers[i]["title"])
            cluster_counts.update(toks)
            cluster_counts.update(zip(toks, toks[1:]))

        sub_areas = []
        if k > 1:
            assign = _kmeans(emb[idx], k, seed=42 + cid)
            for j in range(k):
                sub = idx[assign == j]
                if len(sub) < 5:
                    continue
                scenter = umap[sub].mean(axis=0)
                rel = (scenter - center) / radius
                label, keywords = _label([papers[i]["title"] for i in sub], cluster_counts)
                sub_order = sub[np.argsort(-centrality[sub])]
                sub_areas.append({
                    "label": label,
                    "keywords": keywords,
                    "paper_count": int(len(sub)),
                    "cx": round(float(rel[0]), 3),
                    "cy": round(float(rel[1]), 3),
                    "recent_share": round(float((years[sub] >= max_year - 1).mean()), 3),
                    "top_papers": [{
                        "id": papers[i]["id"], "title": papers[i]["title"],
                        "year": int(years[i]) or None,
                    } for i in sub_order[:3]],
                })
            sub_areas.sort(key=lambda s: -s["paper_count"])

        meta = names[str(cid)]
        briefs[str(cid)] = {
            "id": cid,
            "name": meta.get("name", f"Cluster {cid}"),
            "description": meta.get("description", ""),
            "paper_count": n,
            "year_min": int(valid.min()) if len(valid) else None,
            "year_max": int(valid.max()) if len(valid) else None,
            "year_histogram": hist,
            "growth_recent": round(growth, 3) if growth is not None else None,
            "king_papers": kings,
            "sub_areas": sub_areas,
            "schools": None,
            "debates": None,
            "open_questions": None,
        }

    return {
        "field": "Machine Learning",
        "paper_count": len(papers),
        "max_year": max_year,
        "clusters": briefs,
    }


def main() -> None:
    brief = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(brief))
    sizes = [len(b["sub_areas"]) for b in brief["clusters"].values()]
    print(f"[briefs] {len(brief['clusters'])} clusters -> {OUT}")
    print(f"[briefs] sub-areas per cluster: min {min(sizes)}, max {max(sizes)}")


if __name__ == "__main__":
    main()
