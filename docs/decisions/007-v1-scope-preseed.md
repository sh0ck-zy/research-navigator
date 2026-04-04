# ADR-007: V1 Scope for Pre-Seed

## Status
Accepted

## Date
2026-04-04

## The Problem (one sentence)

Researchers entering a new field spend 2-3 months reading blindly before they understand the landscape — what the sub-topics are, how they relate, what's been done, and where the opportunities are.

## What V1 Does (one sentence)

You type a research field, you see the map. In 30 seconds, not 3 months.

## The User Journey (V1)

```
1. Land on homepage → see the pitch, one input field
2. Type "LLM Safety" → loading (10-30 sec, real-time processing)
3. See the map → clusters with real names, sizes, connections
4. Hover a cluster → see sub-topics, paper count, key papers
5. Click a cluster → zoom in, see individual papers, abstracts
6. Click a paper → see metadata, abstract, citations, nearest neighbors
7. Share → screenshot / link to this map
```

That's it. Nothing else.

## What V1 Does NOT Do

- No user accounts (v2)
- No saving or bookmarking (v2)
- No paper management or library (v2)
- No writing tools or synthesis (v2)
- No AI chat or agents (v2)
- No collaboration (v2)
- No custom uploads (v2)
- No alerts or monitoring (v2)

## What Pre-Seed Needs to See

1. **Working product** — type a field, see the map. Real data, not mock.
2. **Signal of demand** — Reddit post with traction, waitlist signups, early users.
3. **Vision deck** — how this becomes Phase 2 (platform) and Phase 3 (infra).
4. **Founder with momentum** — shipped alone, got users, understands the market.

## Technical Scope

### Must have (launch)
- Data pipeline: arXiv papers → embeddings → clusters → named clusters
- API: query by field → return clusters + papers + relationships
- Frontend: interactive map visualization (design TBD)
- Search: type a field, get a map
- Paper detail: click → see abstract, citations, neighbors
- Shareable: unique URL per map
- Landing page with waitlist
- Deployed on the web

### Fields supported at launch
- Machine Learning (arXiv cs.LG, cs.AI, cs.CL, stat.ML)
- Expand to more fields post-launch

### Data scale
- ~50k-100k papers for ML (enough for comprehensive coverage)
- Embeddings: sentence-transformers (all-MiniLM-L6-v2 or similar)
- Clustering: UMAP projection + Leiden community detection
- Cluster naming: LLM reads top papers per cluster → generates name + description

## Pre-Seed Milestones

| Milestone | What | Goal |
|-----------|------|------|
| M1 | Backend pipeline working (data → embeddings → clusters → API) | Can query "LLM Safety" and get real clusters |
| M2 | Frontend with visualization (design TBD but functional) | Can see and interact with the map |
| M3 | Public launch (Reddit, HN, ProductHunt) | 500+ signups or meaningful engagement |
| M4 | Pre-seed deck + metrics | Ready to talk to investors |

## What Makes This Fundable

- **Problem is validated** — 55 real researcher quotes, published studies on research overload
- **Market is massive** — 9M+ researchers globally, $20B+ knowledge management market
- **No one does this** — zero tools give a bird's-eye view of a research field
- **Tech is proven** — founder already built the core pipeline (embeddings + community detection) in university projects
- **Vision scales** — field maps → platform → research infrastructure (unicorn path)
- **Timing** — AI tools for research are exploding, but no winner has emerged for discovery/mapping

## Budget to Get Here

- €0 — founder builds with AI tools
- ~€50-100/month for hosting + LLM API
- Timeline: 4-6 weeks to M2, 6-8 weeks to M3
