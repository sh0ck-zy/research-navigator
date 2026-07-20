# Reference — mined assets from predecessor projects

This idea had **four attempts before `clarity-research`**. Rather than keep
~674MB of old code in your head, this file catalogues the pieces worth reusing
and points to exactly where they live. All four remain on GitHub
(`github.com/sh0ck-zy/*`) and as local sibling directories in `~/Projects/`.

> This is a map, not a copy. The source files stay in their repos so they don't
> go stale here. When you need one, open it at the path listed.

## The lineage

| # | Project | Dates | GitHub | What it was |
|---|---------|-------|--------|-------------|
| 1 | `rip` | May–Sep 2024 | `sh0ck-zy/rip` | First stab: Next.js UI, mocked data, d3 force-graph |
| 2 | `research-papers-network` | Nov–Dec 2024 | `sh0ck-zy/research-papers-network` | **Academic** — Network Science course project (w/ Marc Meijers). The algorithm seed. |
| 3 | `navvv-kg-project` | Mar 2025 | `sh0ck-zy/navvv-kg-project` | Neo4j knowledge-graph prototype |
| 4 | `research-navvv` | Dec 2024–Mar 2026 | `sh0ck-zy/research-navvv` | Most polished predecessor: monorepo, Three.js galaxy, Supabase |
| 5 | **`clarity-research`** | Apr 2026 → | `sh0ck-zy/research-navigator` | **This repo — everything converged here** |

---

## 🔴 Security — do this first

`navvv-kg-project/config/config.yaml` has a **live-looking OpenAI key
(`sk-proj-…`) committed into git history**, plus a default Neo4j password.
It is public on GitHub. **Revoke the key at platform.openai.com**, then it can
be scrubbed from history (BFG / git-filter-repo).

---

## What to reuse, and where it lives

### From `research-navvv` (the richest donor — clean architecture)
- `engine/arxiv_build.py` — deterministic arXiv sampler + spatial layout:
  `sample_balanced_papers`, `text_feature_vector`, `build_projection_matrix`,
  `normalize_coordinates`, `shape_milky_way`, plus a `CLUSTER_SPECS` taxonomy.
- `apps/web/public/demo/nodes.json` (2.2MB) — real arXiv papers with
  precomputed 3D coords + clusters. Ready-made demo data.
- `apps/web/src/lib/galaxy/search.ts` — hybrid search (exact-substring ranked +
  Fuse.js fuzzy fallback, tunable weights). `scripts/bench_search.mjs` benchmarks it.
- `apps/web/src/lib/galaxy/schema.ts` + `docs/data-contract.md` — a **Zod node
  schema** with legacy-field normalization. This typed data-contract is cleaner
  than the current galaxy's vanilla-JS approach — worth adopting.
- `supabase/functions/_shared/claude.ts` — Claude PDF→graph extraction contract:
  entities (`paper/author/topic/method/dataset/metric`) + relations with
  confidence. Strong reusable extraction schema.
- `supabase/migrations/20260219233000_pilot_core.sql` — Postgres + RLS, invite
  gating, AI cost cap. A ready pilot-backend pattern if NAV needs accounts.
- `apps/web/src/components/galaxy/uiTokens.ts` + `final-report.json` — a
  "Clean Dark Minimal" token set and a UI-quality rubric (node hierarchy,
  palette, spatial distribution, motion) — reusable as a design QA checklist.

### From `research-papers-network` (the methodology / whitepaper)
- `embedding_generator.py` — embed pipeline with hash-based npz caching.
- `connection_creator.py` — `create_knn_connections` and
  `create_radius_connections` + `compute_distance_statistics` (threshold picking).
- `data_loader.py` — chunked streaming loader for large arXiv JSON.
- `prompts.txt` — the LLM prompt pair for community → description + topic label.
- `final_report.ipynb` — the graded write-up: the rationale for kNN-vs-threshold
  graphs (sparse = niche, dense = broad). Good design-doc material.

### From `navvv-kg-project` (graph analytics ideas)
- `src/knowledge_graph/queries.py` (~490 LOC) — 12 named analytical Cypher
  queries: dataset trends by year, dataset co-occurrence, method/dataset combos,
  author influence, collaboration networks, dataset transition patterns. These
  encode "non-obvious insight" features for a future KG layer.
- `config/config.yaml` — the LLM extraction prompt template (structured JSON:
  subfield/datasets/methods/results) + a curated ~30 canonical-dataset seed list.
  ⚠️ also holds the leaked key — copy the schema, not the file.
- `docs/research/` — business-case + competitor teardown (Semantic Scholar, ORKG,
  Scite). Positioning material.

### From `rip` (earliest — mostly ideas)
- `backend_plan.md` — the most valuable file: concrete backend design decisions
  with rationale (PyMuPDF vs pdfminer, GPT vs fine-tune, Neo4j vs Postgres,
  hybrid embedding+graph recs). Idea-mining, nothing was built.
- `frontend/src/app/EnhancedResearchNavigator.tsx` — the d3 `renderGraph()`
  force-directed graph (lines ~47–137) if a 2D graph view is ever wanted.
- `StarryBackground.tsx`, `LoadingAnimation.tsx` — small self-contained visuals.

---

## Verdict

Nothing here needs reviving — `clarity-research` supersedes all four. The
highest-leverage borrows are: **`research-navvv`'s Zod data-contract + hybrid
search + Claude extraction schema**, and **`research-papers-network`'s
kNN-vs-threshold methodology**. Everything else is idea/reference material.
</content>
