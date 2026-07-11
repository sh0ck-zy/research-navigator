# Research Navigator — running it

Project-based research workspaces: a research question + 20–300 papers → a
living, source-linked understanding (the **Living Research Board**). This is
the pivot away from the galaxy Observatory (which stays on the
`observatory-mvp` branch). v0.1 runs **locally** — no deploy.

## One-time setup

```sh
# Python deps (adds bibtexparser, rispy, python-multipart on top of the pipeline deps)
pip install -r requirements.txt

# Frontend deps + build
cd frontend-app && npm install && npm run build && cd ..
```

## Run (single process — serves the built app)

```sh
uvicorn backend.app:app --port 8000
# open http://localhost:8000
```

The DB (`data/navigator.db`) is created by migrations on first start. It is
gitignored — each machine keeps its own projects.

### Dev mode (hot-reload frontend)

```sh
uvicorn backend.app:app --port 8000        # terminal 1 (API)
cd frontend-app && npm run dev              # terminal 2 → http://localhost:5173
```

Vite proxies `/api` to `127.0.0.1:8000` (must be `127.0.0.1`, not `localhost`
— IPv6 gotcha).

## AI board generation (needs a key)

Board drafting calls Claude. Everything else — projects, import, enrichment,
library, search, exports — works without a key.

```sh
export ANTHROPIC_API_KEY=sk-ant-...        # or `ant auth login`
export NAVIGATOR_MODEL=claude-sonnet-5     # optional; default. Also: claude-opus-4-8, claude-fable-5
uvicorn backend.app:app --port 8000
```

`GET /api/health` reports `board_generation_available`; without a key the
Generate button is disabled and `POST …/board/generate` returns 503.
Cost is roughly $0.12 (50 papers) to $0.58 (100). Generation is capped at
100 papers per run — filter the library first for bigger projects.

## Demo data (no network, no model)

```sh
python -m backend.scripts.seed_demo --reset
# → an "Explainable AI methods for fMRI analysis" project with ~60 real
#   neuro papers, embeddings copied from the precomputed corpus. Open the
#   printed URL.
```

## The loop

1. **New project** — research question (+ optional hypothesis, scope).
2. **Library** — import a Zotero `.bib`/`.ris`, or add by DOI / arXiv /
   OpenAlex URL. Papers enrich from OpenAlex (journal DOIs) or the arXiv API
   (preprints); set read-status per paper; semantic + keyword search.
3. **Board** — Draft it. Claude proposes concepts, claims, evidence (each
   quoting a cited abstract verbatim), open questions, next actions. You
   accept / edit / reject. Every AI item cites its papers; uncited or
   misquoted items are dropped before you ever see them.
4. **Export** — `.bib` (library) and board `.md` (curated, with citations).
5. **Return tomorrow** — the project shows the state of your research, not a
   chat history.

## Architecture notes

- **Single write path** (`backend/services/commands.py`): every mutation
  appends to an append-only `events` log and applies state in one
  transaction, so who-changed-what (user vs AI) is recorded by construction.
  A process-global lock serializes `events.seq` allocation across the
  foreground request and background jobs.
- **Per-project search** is brute-force numpy cosine over MiniLM vectors
  stored as BLOBs — no FAISS at this scale.
- **Background jobs** (enrichment, board generation) are FastAPI
  `BackgroundTasks` + a `jobs` table polled by the UI.

Ephemeral-disk hosts (HF Spaces) would wipe `navigator.db` on restart, which
is wrong for real projects — hence local-only for the pilot.
