# ADR-005: Launch Scope and Expansion Strategy

## Status
Accepted

## Date
2026-04-04

## Context
We need to decide whether to launch with a global research map (all fields) or focus on a niche. This affects data pipeline complexity, validation speed, and positioning.

## Decision
**Launch with ML/AI only. Expand field by field.**

### Why ML/AI first (for public launch)
- Existing tech: Joao already processed 10k ML papers with embeddings + community detection
- Data access: arXiv (cs.LG, cs.AI, cs.CL, stat.ML) is open and well-structured
- Distribution: r/MachineLearning (3M+), r/PhD, ML Twitter — largest online research community
- Pain is acute: fastest-growing field, highest paper volume, maximum overload
- We understand the domain enough to validate quality of results

### Why AI + Neuroscience + Bioengineering (for internal validation)
- Potential co-founder (PhD friend) works at the intersection of AI, neuroscience, and bioengineering (brain-reading machines, etc.)
- Interdisciplinary research = pain is 10x worse (different jargon, different communities, papers don't cross-reference)
- This is the "Valley of Death" problem: knowledge doesn't flow between domains
- A map showing how AI, neuroscience and bioeng intersect is more impressive than just ML
- For investors: "works across disciplines" is a stronger proof point than "works in one field"
- Perfect test case: if it works for his messy interdisciplinary field, it works for anything

### Strategy
- **Internal testing:** friend's interdisciplinary field (AI + neuro + bioeng)
- **Public launch:** ML/AI (where the Reddit audience is)
- Both run in parallel — same tech, different datasets

### Expansion path
1. ML/AI (launch — prove it works)
2. Adjacent CS sub-fields: NLP, CV, Robotics, Security
3. New domains: Biomedicine (PubMed), Physics (arXiv), Chemistry
4. All research (OpenAlex — 200M+ papers)
5. Endgame: the map of all human knowledge

### For investors
The pitch is: "We proved this in ML. The model generalizes. OpenAlex gives us 200M papers across every field. We expand domain by domain, each one unlocking a new market (pharma R&D = $billions, climate = $billions, etc.)"

## Consequences
- Data pipeline v1 only needs arXiv ML papers
- Quality bar is high for ML — our first users know the field deeply and will spot errors
- Don't build domain-agnostic abstractions yet — optimize for ML, generalize later
- Marketing is ML-focused: "The map of Machine Learning research"
