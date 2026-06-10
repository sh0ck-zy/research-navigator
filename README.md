# Clarity Research

> Build the platform where the world does research.

## What is this repo?

This is not just code. This is the full knowledge base of a product from zero to launch — research, decisions, product definition, and code. Everything needed to understand **why** we built what we built, not just **what** we built.

## Status

**Stage:** Pre-product — defining what to build.

## Structure

```
clarity-research/
├── research/              # Everything we learned before writing code
│   ├── domain/            # How the research world works (workflows, tools, pain points)
│   ├── product/           # Pain maps, feature candidates, user quotes
│   ├── market/            # TAM, pricing, business models
│   └── competitors/       # What exists, what works, what doesn't
├── docs/
│   ├── decisions/         # ADRs: every major decision, with context and reasoning
│   └── playbook/          # Reusable methodology (launch, distribution, validation)
├── design/                # UI/UX explorations, mockups, prototypes
├── backend/
│   ├── pipeline/          # OpenAlex ingest → embed → UMAP → Leiden → name → export
│   └── api.py             # FastAPI: semantic search (FAISS) + serves the frontend
├── frontend/              # The Observatory — Three.js map (Vite + ES modules)
│   ├── src/               # scene, labels, clusters, papers, search, nav, stats, loop
│   └── data/              # map_data.json produced by the pipeline (gitignored)
└── data/                  # Pipeline caches: raw papers, embeddings, projections (gitignored)
```

## Running it

```bash
# Backend (terminal 1) — pipeline outputs must exist (python backend/pipeline/run_pipeline.py)
source .venv/bin/activate
uvicorn backend.api:app --port 8000

# Frontend dev (terminal 2)
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxies /api to :8000)

# Production: build once, then FastAPI serves everything at :8000
cd frontend && npm run build
```

Deploy to Hugging Face Spaces (Docker): see [docs/deploy-hf-spaces.md](docs/deploy-hf-spaces.md).
Switch corpus with `python backend/pipeline/run_pipeline.py --field neuro|ml`.

## Principles

1. **Research before code.** Understand the problem deeply before building.
2. **Document decisions, not just outcomes.** Every major choice gets an ADR with context, options considered, and reasoning.
3. **Researcher in control.** AI augments, never replaces. The human thinks, reads, writes.
4. **Launch ugly, iterate fast.** Perfect is the enemy of shipped.
5. **One thing at a time.** No "Research OS". One killer feature, one launch, one audience.
