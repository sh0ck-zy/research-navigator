# ADR-006: Visualization Approach — Island Map

## Status
Accepted

## Date
2026-04-04

## Context
Research is abstract — unlike the Google Language Explorer which uses a world map, we have no natural geographic anchor. We need a visual metaphor that makes research fields feel explorable, readable, and shareable.

## Options considered
1. **Force-directed graph** — points in space, proximity = similarity. Problem: looks like a blob, hard to read, not shareable.
2. **Treemap / bubble map** — sized areas per cluster. Clear but boring, no exploration feeling.
3. **Islands / continents** — clusters as organic landmasses in an ocean, proximity = relatedness. Zoom to explore sub-islands. Gaps = water between islands.
4. **3D cosmos / galaxy** — impressive but hard to read, impossible to screenshot usefully, bad on mobile.

## Decision
**Option 3: Islands / continents.**

The metaphor: research fields as an archipelago. Each island is a research cluster. Island size = volume of research. Water between islands = gaps. Zoom into an island to see sub-islands (sub-topics) and eventually individual papers.

Example: type "Machine Learning" → see archipelago with islands: "Deep Learning" (large), "Reinforcement Learning" (medium), "Causal Inference" (small). Zoom into "Deep Learning" → sub-islands: "Transformers", "Diffusion Models", "Architecture Search".

### Why this works
- Provides the geographic anchor that abstract data lacks
- 2D but feels like a world — invites exploration
- Zoom in/out is natural: field → sub-field → papers
- Screenshots are readable and shareable (viral potential)
- Differentiating: nobody does research maps as "knowledge islands"
- Gaps are visible as water/empty space — intuitive

### Technical approach
- Use UMAP/t-SNE to project embeddings to 2D
- Draw organic contours around clusters (detected via Leiden algorithm)
- Render as interactive web map (canvas-based, not Three.js)
- Zoom levels: L1 = full field, L2 = sub-clusters, L3 = individual papers

## Consequences
- No 3D for v1 (can add as "immersive mode" later)
- Need good contour/island rendering — this is the visual differentiator
- Map must be beautiful — Apple-grade, editorial quality
- Performance matters: must feel instant, smooth zoom
