# ADR-001: Target User

## Status
Accepted

## Date
2026-04-04

## Context
We need to decide who we're building for first. The field map feature has broad appeal but we need a specific audience for launch and distribution.

## Options considered
1. **PhD students** — highest pain (new to their field, overwhelmed), most active on Reddit, best for viral distribution, least money
2. **Postdocs** — experienced, know what they need, some budget
3. **Senior academics / PIs** — have budgets, least likely to try new tools
4. **Industry R&D** — have money, different workflow

## Decision
**PhD students first, specifically in CS/ML/AI.**

Why:
- Highest pain: they're new to their field and the overload is worst at the start
- Most active online: r/PhD (700k+), r/MachineLearning (3M+), r/GradSchool
- Most willing to try new tools: digital natives, early adopters
- CS/ML because: we understand the data (arXiv), the field moves fast (pain is acute), and it's where we can validate quickest
- Joao's friend is a PhD student — built-in first tester

Expand to other fields and seniority levels after validation.

## Consequences
- All UX decisions optimized for PhD students starting in a new field
- Distribution via Reddit academic subreddits
- Free tier is essential — PhD students have no money
- Monetization comes later (institutional, enterprise) once we have adoption
