# ADR-011: NAV — Knowledge Exploration Universe

## Status
Accepted

## Date
2026-07-19

## Overrides
Reframes ADR-010 (the Observatory-only roadmap). Keeps ADR-005 (ML-first launch scope) and ADR-003 (AI augments, human decides).

## Context
We built two products on two branches and treated them as alternatives:

- **The Observatory** (`observatory-mvp`): a galaxy map of a research field. Strong first impression — but anonymous, ephemeral, nothing to return to. Acquisition without retention.
- **The Research Navigator** (`research-navigator`): project workspaces with a Living Research Board. Retention and a business — but no discovery, cold start (the user must arrive with papers), no top of funnel.

A week of business thinking (July 2026) showed this was a false dichotomy. The pain map already said it: the pain is not lack of tools, it is lack of continuity between discovery → triage → reading → synthesis. The Observatory covers discovery. The Navigator covers synthesis. Neither works alone as a business; together they cover the loop.

## The unit of value
**A researcher can enter an unknown domain and build a mental map in minutes.**

Not papers found, not summaries generated, not smart chat, not organization. This is **compression of expertise**. An experienced researcher carries a mental model:

```
Field
 |
 +-- schools of thought
 +-- fundamental concepts
 +-- conflicts
 +-- historical evolution
 +-- opportunities
```

NAV promises to build an approximation of that model, in minutes instead of months. Every v0 decision is judged against this promise.

## Options considered
1. **Observatory only** — public galaxy, Reddit launch. Pros: wow factor, simple. Cons: one-visit product, no willingness to pay, no retention mechanic.
2. **Navigator only** (the "pivot") — kill the galaxy, local-first workspaces. Pros: retention, spend category. Cons: cold start, no acquisition channel, user must bring their own corpus before seeing any value.
3. **Synthesis** — galaxy as the entry point, research space as the destination, shared intelligence underneath. Pros: covers the full loop; reuses ~70% of what is already built. Cons: requires a new cluster-intelligence layer.

## Decision
Option 3.

**NAV is not a chatbot, not a paper manager, and not only a knowledge graph. NAV is a knowledge exploration universe with intelligence-powered research spaces.**

### Product philosophy
> **NAV does not replace the researcher. It gives every researcher the ability to navigate knowledge at expert speed.**

This is the differentiation. AI-researcher tools and chatbots say *"give me an answer"*. NAV says *"help me understand the territory"*. The answer expires; the territory remains.

### One interface, two scales
Not two products — one product at different zoom levels, like Google Maps (Earth → country → city → street → home):

```
Field  →  Cluster  →  Research question  →  Your project
(Explore)              (Create)
```

- **Galaxy = acquisition + discovery layer — and product.** Not marketing. If someone spends 20 minutes exploring a scientific field without creating an account, they already received value. Anonymous, public, the "wow".
- **Research Space = creation interface.** Personal, persistent, holds the researcher's state. This is what they return to and what they pay for.

### The engine: Knowledge Intelligence Layer
Not called a Knowledge Graph in v0 — there is no true KG yet, and the name would set the wrong expectation. The layer grows:

```
v0:  embeddings, clustering, extraction, verification, summaries
v1:  ontology, entities, relations
v2:  reasoning engine, autonomous discovery
```

The vision stays; the naming doesn't block execution.

### The killer screen: Cluster Intelligence Page
The loop is defined; now the experience. One screen must exist:

```
Hallucination in LLMs
2,431 papers · 2019–2026

THE LANDSCAPE

                Verification
                    ↑
                    |
RAG ←──────── Hallucination ──────── Self-Critique
                    |
                    ↓
              Model Editing

Major schools:
1. Retrieval-Augmented Generation — hallucinations are missing information
2. Training-time alignment — hallucinations are a model behaviour problem
3. Verification systems — intelligence needs external checking

Foundational papers:
⭐ Constitutional AI

Current debates:
"Are hallucinations a bug or a feature?"

Open questions:
- Can models know when they are wrong?
- Can verification scale?
```

The map attracts. The intelligence convinces. This page is the "Kimi moment".

### MVP phasing: static intelligence first, interactive second
**v0.1 — Static intelligence (batch pipeline, no agents, no real-time):**
```
500 papers → clusters → LLM analyst → cluster briefs → website
```

**v0.2 — Research Space:**
```
Create Space → import cluster → Board populated → user explores
```

**v0.3 — Personal intelligence:**
```
Your research + NAV global knowledge = research copilot
```

### v0 scope
Not the galaxy of all science — **one small galaxy, extremely intelligent**: ML only, 500–5000 papers (per ADR-005). The first experience: open NAV → see the ML map → explore a cluster → receive cluster intelligence → create a Research Space seeded from that cluster → the Living Board takes over.

### The one thing v0 must prove
A researcher enters an unknown domain and builds a mental map in minutes. Not the chat — the exploration.

## Consequences
- The two branches merge into one product; the Observatory is no longer a dead end
- **Cluster intelligence is the new work**: LLM analyst pass over the corpus (schools, debates, gaps, movement), computed once and cached — static, cheap, amortized
- **The bridge galaxy → space must be built**: "I want to study X" creates a space seeded with the cluster's papers
- No ontology UI, no graph editor, no real-time agents in v0
- The Navigator's local-only constraint is revisited: galaxy is public/anonymous, spaces are personal/account. Deploy strategy needs a follow-up ADR
- `research/market/` still needs the business model: who pays, for what, at what price
- Success metric for v0: time-to-mental-map for a researcher entering an unfamiliar subfield, not signups
