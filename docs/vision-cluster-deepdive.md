# Cluster Deep-Dive Vision (Level 2)

> When entering a cluster, it should be a world in itself — not just a zoomed-in scatter plot.

## Experience

### 1. Camera framing
Camera auto-positions to frame the sub-graph optimally. Not a generic zoom — calculated to show what matters.

### 2. Internal dynamics
Papers are not loose points — they have relationships. Show:
- Citation loops (who cites who)
- Bridge papers connecting sub-communities within the cluster
- Sub-groups / micro-communities (Leiden level 2)

### 3. Consensus vs. controversy
- Papers that agree → strong links, glow/nebula effect, grouped visually
- Papers that contradict → red links, tension zones
- Strong consensus areas → pulsation, sparkling, cintilar effects

### 4. Visual effects as information
Effects communicate meaning, not decoration:
- Pulsation for high-importance papers
- Glow/nebula for consensus zones
- Sparkling for trending/recent papers

### 5. Neighbor context
Adjacent clusters visible at edges of view, showing where this cluster touches other research areas.

## Pipeline data required
- **Citation graph** — Semantic Scholar API or OpenAlex
- **Concordance analysis** — Claude API batch to detect agreement/contradiction
- **Sub-communities** — Leiden clustering within each cluster (level 2)
- **Real importance** — citation count, PageRank on citation graph

## Priority
Level 2 feature. Level 1 (macro landscape storytelling) must be solid first for Reddit launch. Build citation pipeline when ready, then layer visuals on top.
