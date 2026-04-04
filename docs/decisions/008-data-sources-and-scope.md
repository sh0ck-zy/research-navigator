# ADR-008: Data Sources and Scope

## Status
Accepted

## Date
2026-04-04

## Context
We need to decide exactly what data we ingest, from where, and how much. This affects pipeline complexity, cost, and quality of the map.

## Key Questions and Answers

### Q: One field or multiple?
**Launch: ML/AI only.** One field, done extremely well. Expand after validation.

### Q: What data sources?

**Primary: OpenAlex (free, CC0, comprehensive)**
- 250M+ works, all fields, all metadata
- Includes: title, abstract, authors, citations, references, concepts, institutions
- API: free, generous rate limits
- Why over arXiv alone: arXiv is CS/physics-heavy, OpenAlex covers everything and includes citation data that arXiv doesn't have
- Why over Semantic Scholar: OpenAlex is fully open (CC0), S2 has rate limits and restrictions

**Secondary: arXiv (for full-text abstracts in CS/ML)**
- Our existing 10k dataset is from arXiv
- Excellent for CS/ML/AI specifically
- Complements OpenAlex with richer abstract data

**Not using (for now):**
- Semantic Scholar API — rate limited, adds complexity, OpenAlex covers same data
- PubMed — medicine, not needed for ML launch
- Scopus/WoS — paywalled, institutional access needed
- Full paper text — abstracts are enough for embeddings and clustering

### Q: How many papers for launch?
**50k-100k papers in ML/AI.** Enough for comprehensive coverage without being slow.

Breakdown:
- arXiv categories: cs.LG, cs.AI, cs.CL, cs.CV, cs.NE, stat.ML
- Time range: 2018-2026 (recent enough to be relevant)
- Filter: must have abstract

### Q: What metadata per paper?
- Paper ID (DOI or arXiv ID)
- Title
- Abstract
- Authors (names + institutions if available)
- Year of publication
- Venue/source (conference/journal)
- Citation count
- References (papers it cites)
- Categories/concepts

### Q: What do we compute?
- Embedding per paper (from abstract, sentence-transformers)
- 2D projection (UMAP)
- Community/cluster assignment (Leiden algorithm)
- Cluster name + description (LLM-generated from top papers)
- Inter-cluster relationships (based on cross-citations and embedding proximity)
- Key papers per cluster (by citation count)

### Q: Do we need real-time data?
**No.** For V1, we process a batch and serve it statically. Update weekly or monthly. Real-time ingestion is V2.

## Decision

```
Data source:     OpenAlex (primary) + arXiv (secondary)
Scope:           ML/AI only (cs.LG, cs.AI, cs.CL, cs.CV, cs.NE, stat.ML)
Scale:           50k-100k papers
Time range:      2018-2026
Update cadence:  Batch (weekly/monthly), not real-time
Metadata:        title, abstract, authors, year, venue, citations, references, categories
Computed:        embeddings, UMAP 2D, Leiden clusters, LLM cluster names, key papers
```

## Consequences
- Pipeline is batch-oriented, simpler to build and debug
- OpenAlex API is free — no cost for data acquisition
- 50k-100k papers is manageable on a single machine
- Can expand to more fields by just changing the OpenAlex query filter
- Weekly/monthly updates mean the map is slightly stale but always consistent
