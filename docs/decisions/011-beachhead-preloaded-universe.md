# ADR-011: Beachhead, Preloaded Universe, and the V1 Whiteboard

## Status
Accepted

## Date
2026-07-20

## Overrides
- ADR-007 (partially): the "type a field → we build the map" input model is **replaced** by a preloaded universe. Prompt-to-map is postponed as a post-launch power feature ("Expeditions").
- ADR-006 (partially): resolves the contradiction between the ADR (2D islands) and what was actually built (3D galaxy). The decision is now **2.5D**: flat precomputed layout, pan/zoom only, no rotation. We keep the galaxy aesthetic (it is the brand and the viral asset) but remove the 3D chaos the ADR correctly warned about.

## Context
The current build has a strong concept and vibe but chaotic UX: everything visible at once, 3D rotation that adds cost without information (the Z axis is literally `sin/cos(cluster index) + random`), label collisions, no focus states, no shareable state, no persistence. Meanwhile the go-to-market analysis concluded that our only unfair advantage is that the galaxy is inherently screenshot-able, and that growth must come from: galaxy (acquisition engine) + territory (retention engine).

## Decisions

### 1. Beachhead: mechanistic interpretability
Launch with **one subfield mapped completely**, not generic ML. Mechanistic interpretability wins because:
- The corpus is small enough (est. 3–6k papers) to credibly claim "we mapped ALL of it" — a checkable claim the community will verify, debate, and share.
- It is the most Twitter-native research community in ML (Olah, Nanda, Anthropic interp team), with an existing culture of roadmaps and open-problem lists (static artifacts we replace).
- Brand fit: "The Observatory" — a telescope for people making the black box visible.
- Freshness burden is survivable at interp's publication rate.

Expansion path: interp → AI safety/alignment → reasoning/post-training → agents → all of ML → beyond ML. Each field is a fresh viral launch to a new community.

### 2. Input model: preloaded universe + search-as-teleport
The knowledge is preloaded. Search never returns a list — it flies the camera to the region and highlights matches. Upload-papers and prompt-to-map are post-launch features.

### 3. The galaxy is the orientation layer, not the work layer
Architecture is a **zoom continuum** (like Google Maps):

| Zoom level | Content | Purpose |
|---|---|---|
| Universe | Cluster constellations, no individual papers | Pick a territory (viral moment) |
| Cluster | Sub-clusters + ~10 landmark papers | Understand the field's shape |
| Neighborhood | Local citation graph around one paper | Actual research work |
| Paper | Clean reading view, AI brief, references | Read, save, cite |

### 4. V1 feature whiteboard (each justified by one engine)

**Acquisition engine:**
1. Navigable preloaded galaxy (zoom continuum) — it is the ad.
2. Complete, verifiable interp corpus — the claim IS the marketing.
3. Shareable views + OG images — 100% of our distribution channel.
4. Landing straight into the product, zero signup — every wall kills the viral spike.

**Retention engine:**
5. Library + fog of war in localStorage — the answer to "why come back Tuesday"; explored territory permanently glows.
6. AI briefs per cluster + landmark papers — converts "whoa, pretty" into "this is useful" (session depth).
7. Search-as-teleport — imports the Scholar habit into our differentiator.

**Explicitly cut from V1** (with the defense): upload papers, prompt-to-map, trails/quests, accounts+sync (localStorage covers 90%), weekly digest, multi-provider AI routing, paywall. Map is always free; intelligence and memory are what will be paid later.

### 5. User journeys (MVP)
- **Journey A — "enter a new field":** land → see the field's shape in 30s → zoom a cluster → read AI brief → save 5–10 landmark papers → territory starts glowing.
- **Journey B — "find something specific":** search → teleport → paper in context (neighbors, lineage, cluster) → discover adjacent papers → save.

We do not invent behavior: these are phases 1–3 of the existing research workflow (orientation, discovery, triage), done with context + memory of coverage. Phases 4–5 (deep reading, reference management) stay with Zotero; phase 6 (synthesis) enters only as AI briefs.

### 6. Landing state (first 5 seconds)
0–1.5s: galaxy materializes (points fade in, slow drift). Then: galaxy in foreground, cluster constellation labels (clickable), one line ("The complete map of mechanistic interpretability. N papers."), one centered search bar. No signup, no tour, no modal, no lens bar. Everything else reveals progressively after first zoom. Shared links skip this state and restore the shared view directly.

## Technical consequences
- Pipeline v2: seed from reference lists of 3–5 interp surveys → OpenAlex citation snowball → keyword filter → target 3–6k papers with `referenced_works` (real citation edges), `publication_year`, venue. Fix the year-parsing bug (export reads `update_date`, ingest writes `year`). SPECTER2 embeddings. Two-level hierarchical Leiden (constellations + sub-clusters). Pre-generated AI briefs per cluster. Split export: light manifest + per-cluster payloads on demand.
- Frontend: migrate from single 65KB `index.html` to Vite + modules; Three.js updated; MapControls with rotation disabled; instanced rendering; LOD (blobs far → landmarks mid → full local graphs near); label budget (~10 max, collision-tested); edges only on selection.
- Repo hygiene: uncommitted local work (Save/Cite/Library, lens bar — seen in 2026-07-11 screenshots, repo HEAD is 2026-04-05) must be committed to a `wip/` branch before the rebuild starts.

## Metrics that decide success
Time-to-first-zoom (<5s) · papers opened per anonymous first session · signup conversion at persistence gate · D7 return of signed-up users (target ≥15%) · share rate per session.
