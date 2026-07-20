# Clarity Research — NAV

> Give every researcher the ability to navigate knowledge at expert speed.

## What is this repo

Not just code — the full knowledge base of a product from zero to launch: the
research we did before building, the decisions (ADRs) with their reasoning, the
product definition, and the working system. It's meant to explain **why** we
built what we built, not only **what**.

## The product (one line)

**NAV is a knowledge-exploration universe with intelligence-powered research
spaces.** One product at two zoom levels, like a map from Earth → street:

```
Field  →  Cluster  →  Research question  →  Your project
   (explore, public)        (create, personal)
```

- **Galaxy** — the public, no-account discovery layer. Open the URL, see a
  scientific field rendered as a navigable map, explore a cluster, receive
  cluster intelligence. This is acquisition *and* value in one.
- **Research Space** — the personal, persistent creation layer. Seeded from a
  cluster, holds a Living Research Board. This is what you return to and pay for.

The full rationale is in **[docs/decisions/011-nav-exploration-universe.md](docs/decisions/011-nav-exploration-universe.md)**
(the accepted direction) and the first-session spec in
**[docs/decisions/012-first-research-journey.md](docs/decisions/012-first-research-journey.md)**.

## Status

**Stage:** NAV v0 in build. The galaxy (explore) and research spaces (create)
are wired into one FastAPI server. Next differentiating work per ADR-011: the
**Cluster Intelligence Page** — the precomputed "landscape of schools" screen.

## Structure

```
clarity-research/
├── research/           # What we learned before writing code
│   ├── domain/         # How the research world works (workflows, pain points)
│   ├── product/        # Pain maps, feature candidates, user quotes
│   ├── market/         # TAM, pricing, business models
│   └── competitors/    # What exists, what works, what doesn't
├── docs/
│   ├── decisions/      # ADRs — every major decision, with context + reasoning
│   ├── playbook/       # Reusable methodology (launch, distribution, validation)
│   ├── research-navigator.md   # Research-spaces run/setup notes
│   └── deploy-hf-spaces.md     # Hugging Face Spaces (Docker) deploy
├── backend/
│   ├── app.py          # NAV unified server: galaxy + spaces + /api (RUN THIS)
│   ├── api.py          # Legacy standalone galaxy API (still the Docker CMD)
│   ├── pipeline/       # OpenAlex ingest → embed → UMAP → Leiden → name → export
│   ├── routers/        # projects, papers, board, search, export, jobs, galaxy
│   ├── services/       # galaxy + supporting logic
│   ├── scripts/        # build_cluster_briefs, seed/demo
│   ├── citations.py    # BibTeX (mirror of galaxy/src/bibtex.js)
│   └── db.py           # SQLite: projects, papers, board (navigator.db)
├── galaxy/             # The Observatory — Three.js map (Vite + ES modules)
│   ├── src/            # scene, clusters, papers, dock, camera, intel, search…
│   └── data/           # map_data.json + cluster_briefs.json (gitignored)
├── spaces/             # Research-spaces SPA — React + Vite + Tailwind (base /app/)
│   └── src/            # ProjectList, Board, Library, NewProject…
├── design/             # UI/UX explorations, mockups, screenshots
├── prototypes/         # Standalone HTML experiments
├── reference/          # Mined ideas + assets from the 4 predecessor projects
└── data/               # Pipeline caches: raw, embeddings, projections (gitignored)
```

## Running it

```bash
# One process serves everything: galaxy at /, research spaces at /app, API at /api
source .venv/bin/activate
uvicorn backend.app:app --port 8000        # open http://localhost:8000

# On a fresh machine, first build both frontends + regenerate map data:
cd galaxy && npm install && npm run build && cd ..
cd spaces && npm install && npm run build && cd ..
python -m backend.pipeline.run_pipeline --field ml   # ingest → embed → UMAP → Leiden → map_data.json
python -m backend.scripts.build_cluster_briefs       # cluster_briefs.json (structural, no LLM)
```

Switch corpus with `python backend/pipeline/run_pipeline.py --field neuro|ml`.
Deploy to Hugging Face Spaces (Docker): see [docs/deploy-hf-spaces.md](docs/deploy-hf-spaces.md).

> **Note:** local dev runs `backend.app` (unified); the Dockerfile still ships
> `backend.api` (galaxy-only). Reconcile before the next public deploy.

## History

This is the 5th and current iteration of a two-year idea. The earlier attempts
live on GitHub (`sh0ck-zy/*`) and their reusable pieces are catalogued in
[reference/](reference/README.md). Inside this repo, the build milestones are
git tags:

| Tag | What it marked |
|-----|----------------|
| `milestone/observatory-mvp`        | Vite refactor, library/BibTeX, HF deploy (Jun 2026) |
| `milestone/research-navigator-pivot` | Project workspaces + Living Research Board (Jul 2026) |
| `milestone/nav-galaxy-dance`       | Galaxy + spaces first unified (Jul 2026) |

`main` is the working line (the former `experience-rebuild`).

## Principles

1. **Research before code.** Understand the problem deeply before building.
2. **Document decisions, not just outcomes.** Every major choice gets an ADR.
3. **Researcher in control.** AI augments, never replaces — no uncited claims.
4. **Launch ugly, iterate fast.** Perfect is the enemy of shipped.
5. **One thing at a time.** One killer feature, one launch, one audience.
</content>
</invoke>
