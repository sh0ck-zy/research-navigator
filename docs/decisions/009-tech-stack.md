# ADR-009: Tech Stack

## Status
Draft — needs Joao's input on frontend preferences

## Date
2026-04-04

## Context
Need to choose a tech stack that:
1. Joao can build solo with AI assistance
2. Is fast to develop and iterate
3. Handles 50-100k papers with interactive visualization
4. Is cheap to host
5. Doesn't lock us in — can scale to Phase 2/3

## Decision

### Backend: Python
**Why:** Joao already knows it. All ML/data libraries are Python. Existing code from university projects is Python. No reason to use anything else.

- **Framework:** FastAPI (async, fast, auto-docs, modern)
- **Data processing:** pandas, numpy
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2)
- **Dimensionality reduction:** UMAP (umap-learn)
- **Clustering:** leidenalg + igraph
- **LLM calls:** anthropic SDK (Claude for cluster naming)
- **Data source clients:** OpenAlex API (requests/httpx), arXiv API

### Database: PostgreSQL + pgvector
**Why:** One database for everything. Relational data (papers, authors, clusters) + vector search (embeddings) in one place. Free tier on Supabase or Neon.

- Papers table: metadata + embedding vector
- Clusters table: name, description, paper count, center coordinates
- Cluster relationships: cross-citation counts between clusters

**Not using Neo4j:** Overkill for V1. We don't need graph traversal queries. Simple SQL with joins covers our needs. Can add Neo4j in V2 if needed.

### Frontend: TBD
**Options to discuss with Joao:**
- **Next.js + Canvas/WebGL** — if we want custom visualization (likely)
- **Next.js + D3.js** — if 2D SVG-based visualization
- **Next.js + Three.js** — if we go 3D (Joao's Gemini code used this)
- **Next.js + deck.gl** — purpose-built for large-scale data visualization on maps

Visualization library depends on the visual direction (the Da Vinci question).

Framework is Next.js regardless — SSR, API routes, deploy on Vercel, Joao likely familiar.

### Hosting / Infra
- **Frontend:** Vercel (free tier, auto-deploy from git)
- **Backend API:** Railway or Fly.io (cheap, Python-friendly)
- **Database:** Supabase (free tier PostgreSQL + pgvector) or Neon
- **LLM:** Claude API (for cluster naming, pay per use)
- **Domain:** ~€10/year

**Estimated monthly cost: €20-50**

### Dev tools
- **Monorepo** in this repo (clarity-research)
- **Claude Code** for AI-assisted development
- **GitHub Actions** for CI/CD (later)

## Repo Structure (proposed)

```
clarity-research/
├── research/          # What we already have (domain, product, market, competitors)
├── docs/              # What we already have (decisions, playbook)
├── design/            # What we already have (prototypes)
├── backend/
│   ├── pipeline/      # Data ingestion + processing
│   │   ├── ingest.py          # Fetch from OpenAlex/arXiv
│   │   ├── embed.py           # Generate embeddings
│   │   ├── project.py         # UMAP 2D projection
│   │   ├── cluster.py         # Leiden community detection
│   │   ├── name_clusters.py   # LLM naming of clusters
│   │   └── relationships.py   # Inter-cluster connections
│   ├── api/           # FastAPI endpoints
│   │   ├── main.py
│   │   ├── routes/
│   │   └── models/
│   ├── db/            # Database models and migrations
│   └── scripts/       # One-off scripts (initial data load, etc.)
├── frontend/
│   ├── app/           # Next.js app
│   ├── components/
│   └── lib/
└── scripts/           # Project-level scripts (setup, deploy)
```

## Consequences
- Python backend means we reuse ~70% of existing university code
- PostgreSQL is boring and reliable — good for solo dev
- Vercel + Railway keeps costs under €50/month
- Frontend visualization library is the only open question — depends on visual direction
