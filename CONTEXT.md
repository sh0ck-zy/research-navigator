# CONTEXT.md — The Observatory: Strategy, State & Build Plan

> **Read this first.** This file is the single source of truth for any coding agent
> working on this repo. It compresses the product strategy, the current state,
> and the exact build plan. ADRs in `docs/decisions/` hold the *why*; this file
> holds the *what* and *where*. If this file and an ADR conflict, this file wins
> (it is newer); then update the ADR.

Last updated: 2026-07-20 · Strategy session distilled into actions.

---

## 1. What this product is (in one paragraph)

**The Observatory** is a preloaded, navigable map of research — starting with a
complete map of **mechanistic interpretability** (est. 3–6k papers). Users land
inside a live galaxy of papers (no signup), zoom through a continuum
(universe → cluster → neighborhood → paper), save papers to a library, and watch
their explored territory permanently glow (fog of war). The galaxy is the
acquisition engine (it is inherently screenshot-able → Twitter); the territory/
persistence is the retention engine. Every feature must serve exactly one of
these two engines — otherwise it is out of scope.

**Tagline logic:** "Researchers fly blind. We give them the map."
**Launch claim:** "We mapped ALL of mechanistic interpretability — N papers" —
a claim specific enough that the community will verify it, debate it, and share
it. That debate IS the distribution.

## 2. Why mechanistic interpretability (the beachhead)

- Corpus small enough to credibly claim completeness (3–6k papers, vs. tens of
  thousands for "agents" or "reasoning")
- Most Twitter-native research community in ML (Olah, Nanda, Anthropic interp
  team); existing culture of roadmaps/open-problem lists we replace
- Brand fit: "The Observatory" — a telescope for people making black boxes visible
- Freshness burden survivable at interp's publication rate
- Expansion path (each = fresh viral launch): interp → AI safety → reasoning/
  post-training → agents → all of ML → beyond ML

## 3. V1 feature whiteboard (the ONLY features that matter)

### Acquisition engine
| # | Feature | Notes |
|---|---------|-------|
| F1 | Navigable preloaded galaxy with zoom continuum | 2.5D, pan/zoom only, NO rotation |
| F2 | Complete verifiable interp corpus | via `ingest_v2.py` (DONE) |
| F3 | Shareable views + OG images | every view state = URL; shared links render as galaxy screenshots in Twitter cards; "share this view" button |
| F4 | Landing straight into product, zero signup | galaxy first, 1 line of text, 1 search bar. No modal/tour/lens bar |

### Retention engine
| # | Feature | Notes |
|---|---------|-------|
| F5 | Library + fog of war in **localStorage** | read/saved papers light up permanently; % coverage per cluster. NO accounts at launch |
| F6 | AI briefs per cluster + landmark papers | pre-generated at pipeline time (~200 words: what it is, the camps, open problems) |
| F7 | Search-as-teleport | search NEVER returns a list page — it flies the camera to the region and highlights matches |

### Explicitly cut from V1 (do NOT build — defense included)
- Upload papers (serves users we already have, brings none)
- Prompt-to-map "Expeditions" (expensive, unpredictable; post-launch power feature)
- Trails/quests (needs curated content; v2 with real usage data)
- Accounts + sync (localStorage covers 90%; signup is the post-launch persistence gate)
- Weekly digest (needs freshness pipeline; week 2–3 post-launch)
- Multi-provider AI routing (one API call suffices in V1; abstraction is a cheap refactor later)
- Paywall (land-grab mode; map always free, intelligence/memory paid later)

## 4. User journeys (MVP)

- **Journey A — "enter a new field":** land → galaxy materializes → see field's
  shape in 30s → click constellation / search → camera flies → read cluster AI
  brief → save 5–10 landmark papers → territory starts glowing.
- **Journey B — "find something specific":** search paper/topic/author →
  teleport → paper in context (neighbors via REAL citation edges, lineage,
  cluster) → discover adjacent papers → save.
- Shared-link visitors skip the landing state: restore exact camera + selection.

### Landing state (first 5 seconds) — spec
1. 0–1.5s: black screen, points fade in progressively, slow camera drift. This
   IS the wow moment (the Twitter screenshot).
2. Stable state: galaxy foreground, clickable constellation labels floating on
   the map, ONE line of text ("The complete map of mechanistic
   interpretability. N papers."), ONE centered search bar (placeholder:
   "Search a paper, topic or author…").
3. Everything else (lens bar, library, filters, briefs) hidden until first zoom.

## 5. Technical architecture (target state)

### Data pipeline (backend/pipeline/) — batch, checkpointed, offline
```
ingest_v2.py      → corpus JSONL (schema v2, real citation edges)   [DONE]
embed_v2.py       → SPECTER2 embeddings (NOT MiniLM — see gotchas)
cluster_v2.py     → 2-level hierarchical Leiden: constellations (~8-12)
                    + sub-clusters (~40-60)
project_v2.py     → UMAP 2D coords, computed offline, stored fixed
briefs.py         → LLM-generated AI briefs per cluster + landmark papers
                    (cached in export; cheap model for naming, strong for briefs)
export_v2.py      → SPLIT output (see below) — NOT one monolithic JSON
```

### Export format (critical — fixes current monolith problem)
- `manifest.json` — clusters (id, name, brief ref, center, radius, color,
  paper_count, landmark paper ids) + global stats. Small, loads instantly.
- `cluster_{id}.json` — full paper payloads per cluster, loaded on demand.
- `edges.json` — sparse adjacency list of REAL citation edges (paper_id →
  [cited_ids]), used only for neighborhood view. NEVER rendered globally.

### Frontend — rebuild as Vite + modules (away from single 65KB index.html)
- Three.js (updated), `MapControls` with rotation DISABLED
- Flat layout with subtle depth cues (parallax, glow falloff) — "2.5D"
- Instanced rendering (InstancedMesh or point sprites) — never one mesh per node
- **LOD:** far = soft glowing cluster blobs (sprites/heatmap) → mid = landmark
  papers only → near = full local graph. Max ~2-3k points on screen ever.
- **Edges only on selection** (selected paper's citation neighborhood)
- **Label budget:** max ~10 labels, chosen by importance, collision-tested
- URL state: camera position + selection encoded; OG image generation per share

## 6. Current state of the repo (what exists today)

- `backend/pipeline/` — v1 pipeline works end-to-end on 10k ML papers:
  ingest → embed → project → cluster → name → export. Keep the pattern
  (checkpointed stages, cache-per-step), upgrade the internals per §5.
- `backend/pipeline/ingest_v2.py` — **NEW (done, committed 2026-07-20)**:
  interp corpus builder. Seeds = reference lists of 3 interp surveys
  (arXiv 2404.14082, 2501.16496, 2407.02646) → OpenAlex snowball 1–2 hops →
  keyword + in-corpus-citation filter → JSONL with real citation edges.
  Filter validated: 50/50 recall on interp arXiv query, 2/60 FP on generic
  LLM query. Run: `python backend/pipeline/ingest_v2.py --mailto YOU@EMAIL --stats`
- `frontend/index.html` — working Three.js prototype (65KB single file,
  Three.js r128 via CDN). Proves the vibe; architecture must be replaced.
- `data/raw/arxiv_ml_subset_10k.json` — old demo corpus (generic ML).
- `docs/decisions/001..011` — ADRs. ADR-011 is the current strategy.
- `research/` — domain research, pain maps. Background reading.

## 7. Known bugs & gotchas in existing code (do not propagate)

1. **3D Z-axis is pure noise**: `_z = sin(clusterIndex*1.3)*40 + cos(i*0.7)*30
   + random`. It carries zero information and causes the "buggy galaxy" feel.
   → New layout is flat (2.5D), Z only for parallax, derived from data (e.g.
   cluster hierarchy), never random.
2. **Year parsing bug**: `export.py` reads `update_date` (old arXiv format)
   but `ingest.py` writes `year` (OpenAlex). Papers ingested via pipeline get
   `year: null`. → `ingest_v2.py` writes `year` directly; downstream must read
   `year` only.
3. **No real citation edges**: v1 `select` never fetched `referenced_works`;
   "connections" are kNN in embedding space. → v2 has real `edges` per paper;
   neighborhood view must use them.
4. **Citation bias**: v1 ingest sorted by `cited_by_count:desc` → corpus is old
   papers only, recent hype missing. → v2 snowball from surveys + keyword filter
   avoids this; do NOT reintroduce a citation-count sort as an inclusion filter.
5. **Monolithic JSON**: `map_data.json` embeds everything incl. abstracts
   (500-char truncated). → split export per §5.
6. **Embeddings model**: ADR-009 says all-MiniLM-L6-v2 — too weak for scientific
   text. Use **SPECTER2** (free via Semantic Scholar API or local model).
7. **Flat clustering**: v1 Leiden is single-level. → need 2 levels
   (constellation + sub-cluster) for the zoom continuum.
8. **Three.js r128 (2021) + OrbitControls autoRotate** → update lib, disable
   rotation entirely, use MapControls.
9. **Repo hygiene**: repo HEAD was 2026-04-05 but screenshots from 2026-07-11
   show uncommitted local work (Save/Cite/Open buttons, Library tab, lens bar).
   That work must be committed to a `wip/` branch BEFORE the frontend rebuild
   (it contains UI ideas worth salvaging, e.g. lens modes, library tab).

## 8. Task list for the coding agent (in build order)

### Phase A — corpus (pipeline)
- [ ] **A1.** Run `ingest_v2.py --stats`; verify corpus lands in 3–6k papers,
  sensible year distribution (should peak 2023–2026), venues mostly
  arXiv/NeurIPS/ICLR/ACL. Tune `STRONG_KEYWORDS`/`MIN_IN_CORPUS_CITES` only if
  corpus is wildly off. Report stats before proceeding.
- [ ] **A2.** `embed_v2.py`: SPECTER2 embeddings for all papers (title+abstract).
  Cache to `.npz`. Checkpointed.
- [ ] **A3.** `project_v2.py`: UMAP 2D on embeddings (cosine metric,
  random_state fixed). Store fixed coords — layout must be reproducible.
- [ ] **A4.** `cluster_v2.py`: 2-level hierarchical Leiden. Level 1 = 8–12
  constellations (tune resolution); Level 2 = sub-clusters within each.
  Expected constellations (sanity check): SAEs/dictionary learning, circuits,
  probing/linear representations, superposition, activation steering,
  evals/benchmarks, foundations/theory, applications/safety.
- [ ] **A5.** `name_clusters_v2.py`: LLM names + 1-sentence descriptions for
  BOTH levels (reuse v1 naming logic, apply per level).
- [ ] **A6.** `briefs.py`: for each constellation + top ~50 landmark papers
  (by in-corpus citation count), generate AI brief (~200 words for clusters:
  what it is, the camps, open problems; ~3 sentences for papers). Cache.
- [ ] **A7.** `export_v2.py`: emit `manifest.json` + `cluster_{id}.json` +
  `edges.json` per §5. Total initial payload (manifest) target < 500KB.

### Phase B — frontend rebuild
- [ ] **B1.** Scaffold Vite + vanilla JS modules (no framework needed yet).
  Keep the visual identity: `#0a0a0a` background, Playfair Display serif for
  titles, Inter for body, additive-blend glowing points.
- [ ] **B2.** Galaxy renderer: instanced point sprites from manifest; LOD
  (blobs → landmarks → local); pan/zoom only; slow idle drift; points fade-in
  entrance animation (reuse timing from v1: fade over 1.5s, UI at 0.6s).
- [ ] **B3.** Zoom continuum states: universe → cluster (context card + king
  papers — salvage logic from v1 `showClusterContext`/`showKingPapers`) →
  neighborhood (citation edges from edges.json) → paper view.
- [ ] **B4.** Landing state per §4 spec (galaxy first, 1 line, 1 search bar,
  claim with real paper count from manifest).
- [ ] **B5.** Search-as-teleport: client-side index (title/authors/cluster
  names) from manifest + lazy cluster payloads; camera fly-to on select;
  highlight matching papers (dim others, per v1 `dimExcept` pattern).
- [ ] **B6.** Label budget system: importance-ranked, collision-tested, ~10 max.
- [ ] **B7.** localStorage library + fog of war: saved/read papers get
  persistent highlight color + per-cluster coverage %; "Library" tab showing
  saved papers (salvage from local wip branch if available).

### Phase C — growth plumbing (launch-blocking)
- [ ] **C1.** URL state: encode camera (x,y,zoom) + selection; restore on load.
  Shared links skip landing animation and restore exact view.
- [ ] **C2.** OG image generation for shared URLs (serverless function or
  pre-rendered fallbacks) — shared links must render as galaxy screenshots.
- [ ] **C3.** "Share this view" button producing a clean static image.
- [ ] **C4.** Minimal analytics events: time-to-first-zoom, papers opened per
  session, share clicks, library saves. (Simple event beacon, no heavy SDK.)

### Definition of done for V1 launch
- All F1–F7 features working on the real interp corpus
- Landing → first zoom < 5s on a normal connection
- A shared link opens the exact shared view with an OG galaxy card
- A returning visitor sees their fog-of-war progress intact

## 9. Hard rules for the coding agent

1. **Do not add features outside §3.** If tempted, open an issue instead.
2. **Do not reintroduce 3D rotation or random Z placement** — ever.
3. **Do not change the visual identity** without explicit instruction (dark,
   serif titles, glowing additive points).
4. **Pipeline stages are checkpointed and cached** — never make a stage that
   re-runs everything on every invocation.
5. **Citation edges come from data, not kNN.** kNN is only for cluster
   connection strength, never for paper neighborhoods.
6. **Map is always free, no signup gates exploration.** Persistence (library
   sync) is the only future signup trigger.
7. **Keep ADRs alive**: any decision that overrides this file gets a new ADR,
   and this file gets updated in the same commit.
8. **Commit early, commit working states.** The repo currently lost 3 months
   of local work once — never again.

## 10. Open questions for the human (not blockers)

- OpenAlex rate limits: use `--mailto` (polite pool). If heavy rebuilds are
  needed, consider downloading the OpenAlex snapshot instead of the API.
- SPECTER2 via Semantic Scholar API has rate limits without a key — get a free
  S2 API key, or run the model locally (allenai/specter2_base).
- Where to host OG image generation (Vercel edge function vs. pre-render).
- The uncommitted local work (Save/Cite/Library, lens bar) — salvage decisions
  happen when it is committed to `wip/`.
