# ADR-002: Core Feature for Launch

## Status
Accepted

## Date
2026-04-04

## Context
From our pain map (55 researcher quotes), the dominant pain is overload (18/55). But "overload" is vague. The actionable reframe is: **researchers can't see their field**. They spend 2-3 months reading to build a mental model that could be visualized in seconds.

No existing tool gives a bird's-eye view of an entire research field. Connected Papers shows one paper's neighborhood. Semantic Scholar is a search engine. Litmaps shows timelines. None show the full landscape with clusters, connections, and gaps.

Inspiration: Google Language Explorer (sites.research.google/languages/language-explorer) — an interactive, beautiful map that makes complex data explorable.

## Options considered
1. **Synthesis workspace (notes → related work)** — high impact but requires deep workflow knowledge we don't have yet
2. **Smart triage ("what to read next")** — hard to differentiate from existing recommendations
3. **Field mapping / visualization** — connects to existing tech (network science project), visual = viral, no one does this well
4. **Full pipeline** — too broad for launch

## Decision
**Option 3: Interactive field map.**

The killer feature: **See the landscape of any research field in 30 seconds.**

User enters a topic (e.g., "LLM Safety") and gets:
- A visual map with semantic clusters (sub-topics)
- Cluster size = volume of research
- Connections between clusters = cross-pollination
- Empty spaces = gaps and opportunities
- Click to zoom into any cluster and see key papers

One sentence: **"Researchers fly blind. We give them the map."**

## Consequences
- Tech stack builds on existing network science project (embeddings, community detection, visualization)
- UI/UX quality is the product — not decoration, but the core differentiator
- Launch angle is visual: screenshots and GIFs sell themselves on Reddit
- Phase 1 scope is clear: one input (topic), one output (interactive map)
- Does NOT include: paper management, writing tools, collaboration, agents
