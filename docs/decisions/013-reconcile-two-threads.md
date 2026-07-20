# ADR-013: Reconciling Two Parallel Threads (A engine, B steering)

## Status
Accepted

## Date
2026-07-20

## Context
Two bodies of work forked from the same commit (`e0cddb6`, 2026-04-05) and were
developed the same week **without knowledge of each other**. The divergence only
surfaced when a repo reorg tried to push `main`:

- **Thread A** — the `experience-rebuild` ladder (`observatory-mvp` →
  `research-navigator` → `nav-galaxy-dance` → `experience-rebuild`). It *built*
  the product: Vite + ES-module galaxy, camera director, LOD rendering, unified
  dock, and the React research-spaces SPA. Its product doc is
  **ADR-011 "NAV — Knowledge Exploration Universe"** (galaxy + spaces synthesis).

- **Thread B** — two commits pushed directly to `main` on 2026-07-20: a sharp
  go-to-market pivot and a validated data pipeline. Its product doc is
  **ADR-011 "Beachhead, Preloaded Universe"** (interp beachhead, 2.5D,
  preloaded universe, search-as-teleport, ruthless V1 scope) plus
  `backend/pipeline/ingest_v2.py` (survey-seeded citation snowball, validated
  50/50 recall on an interp query).

Because both were numbered ADR-011, the repo now carries two files with that
number. This ADR resolves the relationship rather than deleting either.

## The key observation
The threads are **complementary, not competing**. Thread B's ADR is largely a
*specification and wishlist*: "migrate to Vite + modules, LOD rendering,
instanced points, camera controls with rotation disabled." Thread A already
**built ~70% of that**. The genuine deltas are small and concrete:

| Dimension | A (built) | B (decided) | Action |
|-----------|-----------|-------------|--------|
| Frontend arch | Vite modules, LOD, camera, dock | *asked for* the same | keep A |
| Dimension | 3D galaxy | 2.5D, no rotation | flip A's controls |
| Corpus | generic ML (~10k) | interp (~3–6k), real citation edges | run B's `ingest_v2.py` |
| Scope | broad (spaces, expeditions) | ruthless V1 cuts, localStorage persistence | apply B's cut-list |
| Pipeline | old ingest | validated `ingest_v2.py` | adopt B's |

## Decision
Merge both into `main` (done — disjoint files, no conflicts). Then:

1. **ADR-011 "Beachhead, Preloaded Universe" is the operative V1 spec.** It
   defines the beachhead (mechanistic interpretability), the scope cuts, the
   landing state, and the metrics. Build against it.
2. **ADR-011 "NAV — Knowledge Exploration Universe" is the architecture vision.**
   Its galaxy↔spaces zoom continuum and Cluster Intelligence Layer remain the
   long-arc direction; it is not superseded, it is the horizon B narrows toward.
3. **Thread A's code is the substrate.** No rewrite — the built galaxy/spaces are
   the implementation B's ADR asked for.
4. The two ADR-011 files keep their names for historical honesty; this ADR is the
   pointer that explains which is which.

## Consequences — the concrete next steps
- Run `python -m backend.pipeline.ingest_v2 --mailto <you>` to build the interp
  corpus; wire it through embed → Leiden → export so the galaxy loads interp,
  not generic ML.
- Disable 3D rotation in the galaxy (MapControls / lock the Z tumble) → 2.5D.
- Apply B's V1 cut-list: no upload, no prompt-to-map, no accounts in V1;
  Library + fog-of-war in localStorage for retention.
- Reconcile the deploy drift (Dockerfile ships `backend.api`; local runs
  `backend.app`) before the next public deploy.
- Fix the year-parsing bug B flagged (export reads `update_date`, ingest writes
  `year`).

## Not deciding here
Whether to eventually renumber the ADRs, and the business model (who pays, for
what) — both left open, as ADR-011-beachhead and `research/market/` already note.
</content>
