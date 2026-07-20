# Workflows — what NAV actually does

> Committed 2026-07-19. After the W1–W4 evaluation (chat session), we
> committed to **W1+W2 as a single workflow**. W3 (Related Work) is v0.2.
> W4 (Keeping Up) is parked — needs recurring ingest.
>
> Sources: research/domain/research-workflow-e2e.md (phases + handoff
> problem), research/product/pain-map-raw.md (55 quotes), competitor check
> (Elicit = question→report; Consensus = question→answer; both are
> answer-machines). NAV's workflows are built around what answer-machines
> structurally can't do: the territory + your curated state over time.

## The one workflow: Chart a New Territory

**User:** PhD student months 1–6, or a researcher entering an adjacent field
(the canonical case: AI researcher moving into neuro/bioeng — jargon changes,
communities don't cross-reference, pain is 10x).

**Trigger:** "I need to understand X." The question is still vague. Two
realistic front doors:

- **Door A — Territory (W1):** supervisor said *"read up on hallucination"*.
  They arrive with a topic name, nothing else.
- **Door B — Paper Zero (W2):** they just read one paper that felt exactly
  relevant. Real researchers more often start here than from a blank map.

### The flow

```
Door A: topic name          Door B: arXiv ID / DOI
      \                         /
       \___ LOCATE ___________/
              |
        The territory renders:
        schools, king papers,
        movement, debates
              |
        ORIENT (read the brief,
        verify against real papers)
              |
        CLAIM IT — Create Space:
        question + seeded library,
        ranked for reading order
              |
        CHART — triage, read-status,
        Board accumulates the structure
              |
        RETURN tomorrow: the territory
        shows what you charted so far
```

1. **Locate.** Door A: search/click the cluster on the galaxy. Door B: paste
   an arXiv ID → NAV drops a pin where that paper lives → same territory view.
   Both doors converge on the Cluster Intelligence Page.
2. **Orient.** Schools, foundational papers, movement, debates — every
   statement clickable to a real paper. Success test (ADR-012): the expert
   says *"I didn't know that"* or *"that's exactly the debate in my lab."*
3. **Claim it.** Create Space = research question + the territory's central
   papers, pre-ranked as a reading list. No blank library, no cold start.
4. **Chart.** Triage with read-status; the Board accumulates claims/evidence
   with provenance (who said what — user vs AI). This is the handoff the
   workflow doc proved no tool covers: discovery → triage → synthesis with
   zero context loss.
5. **Return.** The unit of retention: the territory remembers what you
   charted. Not a chat history — a map with your progress on it.

### What success looks like
In one hour, the user can explain the field's schools to their supervisor
and owns a prioritized reading list of ~25 papers. Compression of expertise
(ADR-011): the mental model that takes months, approximated in minutes.

### Explicitly out of scope (for this workflow)
- Writing/export (that's W3, v0.2)
- Alerts/digest (W4, parked)
- Chat. NAV never chats. It charts.

## v0.2 preview — W3: Related Work
Import `.bib` → NAV clusters *their own* library into themes → Board drafts
claims per theme with verbatim quotes → curate → export `.md` + `.bib`.
Deadline-driven; this is where willingness to pay concentrates.

## Experience principle (from this workflow)
The user moves constantly **between map and collection** — the feel question
is whether the map is home or the expedition is home. Decided next (see
experience discussion, 2026-07-19 session).
