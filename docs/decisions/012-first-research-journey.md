# ADR-012: The First Research Journey

> Not an architecture decision — a journey spec, recorded as an ADR for continuity. This is where we find out if the UI is a product or just a pretty architecture.

## Status
Draft

## Date
2026-07-19

## Context
ADR-011 defines the architecture and the unit of value (mental map in minutes). It does not define what the first session actually feels like. This doc fixes one single user story in concrete terms. If any step here cannot be built in v0, the ADR-011 phasing is wrong — not the journey.

## The user story
> **I am an AI PhD student interested in hallucinations. I open NAV for the first time. What exactly happens in the first 15 minutes?**

She knows the field. That is deliberate: the hardest critic is an expert. If the map survives her scrutiny, it survives anyone's.

## The journey, minute by minute

**0:00–1:00 — Arrival.**
She opens the URL (from a Reddit post: "the map of ML research"). No landing page, no login wall — the galaxy *is* the landing page. She sees ML rendered as a galaxy: labeled regions (LLMs, Computer Vision, RL…), size = papers, brightness = recent activity. First thought we want: *"this is my field, rendered."*

**1:00–3:00 — Orientation.**
She hovers clusters: name, paper count, growth trend. She clicks **Large Language Models** → the camera zooms into the continent: Pretraining, Alignment, Reasoning, Retrieval, Agents, Evaluation, Hallucination. She is navigating by recognition, not search.

**3:00–6:00 — The killer screen.**
She clicks **Hallucination** → the Cluster Intelligence Page: the landscape of schools (RAG ↔ Verification ↔ Self-Critique ↔ Model Editing), each school with a one-line core idea, foundational papers, current debates, open questions, recent movement. She reads for 2–3 minutes. **This is the compression-of-expertise moment** — a mental model that would take weeks of reading, delivered in minutes.

**6:00–8:00 — Verification.**
She is a PhD student; she does not trust it yet. She clicks a school → sees the actual papers behind it, with quoted evidence. Every statement on the page is clickable to its sources. She opens one foundational paper's abstract. Trust is established here — or lost forever.

**8:00–10:00 — Personal stake.**
She clicks **Create Research Space**. Only now is she asked for anything: her research question — *"Can models know when they're wrong?"* — and an account. The space is created pre-seeded with the cluster's papers and a drafted Living Board. First friction happens *after* value received, never before.

**10:00–15:00 — First return value.**
She triages: marks papers to read, edits one AI claim she disagrees with, adds her own hypothesis. The Board shows open questions and next actions. She closes the tab with three things: a mental map, a reading list, and a space that will be there tomorrow. That is the retention hook.

## What each minute demands from the product
| Minute | Requirement | Consequence for v0 |
|--------|-------------|--------------------|
| 0–1 | Public galaxy, no auth, instant load | Galaxy is the landing page; no marketing site |
| 1–3 | Zoom navigation cluster → sub-clusters | Exists (Observatory), needs cluster metadata |
| 3–6 | Cluster Intelligence Page, precomputed | v0.1 static pipeline; page must load instantly |
| 6–8 | Every AI statement clickable to evidence | No uncited claims rendered, ever (Navigator already drops them) |
| 8–10 | One-click space creation seeded from cluster | The bridge — the only genuinely new backend flow |
| 10–15 | Board editable, persistent | Exists (Navigator) |

## Open questions
1. What if her field is not ML? v0 must say so honestly — and capture the demand ("notify me when your field lands" email).
2. 500 vs 5000 papers: does the galaxy still feel rich at 500? Needs a visual test before committing the corpus size.
3. Foundational papers: ranked by citations/PageRank, not LLM vibes alone — what is the defensible formula?
4. Mobile: out of scope for v0, but the Reddit traffic will be partly mobile. Accept a degraded read-only galaxy there?
5. Where does "recent movement ↑340%" come from? Needs a time-windowed activity metric in the pipeline.

## Success signal
Around minute 5 she says one of two things out loud: *"I didn't know that"* or *"that's exactly the debate in my lab."* Both mean the map matches or extends her expert model. The failure mode is also specific: she spots one wrong school or hallucinated claim — and the trust, and the product, are gone.
