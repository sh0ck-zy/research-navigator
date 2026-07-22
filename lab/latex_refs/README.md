# lab/latex_refs — a citation index from arXiv LaTeX

Our own citation index, built from arXiv e-print **LaTeX source**, parallel to
and never touching the frozen assets (Kùzu graph, clustering, layout,
`ingest_v3.py`, eval). The point is the citation layer no aggregator captures:
**informal URL citations** — `transformer-circuits.pub`, `distill.pub`, and bare
`arxiv.org/abs/*` links in footnotes — where the SAE wave actually lives.

All code lives here; all data under `data/latex/`. v1 scope is **edges +
contexts + a comparison report** — nothing else (no intent classification, no
KG extraction, no writes to the main graph).

## Pipeline

| # | Stage | Module | Reads | Writes (aggregate) |
|---|-------|--------|-------|--------------------|
| 0 | resolve ids | `resolve_ids.py` | corpus (683) | `data/latex/ids.jsonl` + `lab/eval/arxiv_id_resolution.json` |
| 1 | fetch source | `fetch_sources.py` | `ids.jsonl` | `data/latex/fetch.jsonl` + `sources/<Wid>/` |
| 2 | parse refs | `parse_refs.py` | `sources/` | `data/latex/refs.jsonl` |
| 3 | resolve refs | `resolve.py` | `refs.jsonl` + corpus + `ids.jsonl` | `data/latex/resolved.jsonl` |
| 4 | contexts | `contexts.py` | `sources/` + `refs.jsonl` | `data/latex/contexts.jsonl` |
| 5 | compare | `compare.py` | `resolved.jsonl` + corpus `edges` | `data/latex/compare.json` + `lab/eval/latex_refs_audit.md` |

Run each as a module from the repo root, e.g. `python -m lab.latex_refs.fetch_sources`.

## Checkpoint contract (resume)

Every stage writes **one JSON per paper** to `data/latex/ckpt/<stage>/<Wid>.json`,
keyed by OpenAlex id. A crash at paper 400 resumes at 401 (existing checkpoints
are skipped). Writes are atomic (`.tmp` + `replace`). After the loop, each stage
folds its checkpoints into a single tracked `data/latex/<stage>.jsonl`.

`data/latex/ckpt/` and `data/latex/sources/` are git-ignored (regenerable /
large); the per-stage aggregates and the two `lab/eval/` reports are tracked.

## Stage 0 — arXiv-id resolution

Only 182/683 corpus records carry a local arXiv id. The rest are resolved with
**one paced arXiv `api/query` title search each**, accepted only if the top hit
passes a strict gate — we never force a match:

- `title_sim >= 0.92` (rapidfuzz `token_set_ratio`, normalized)
- `author_overlap >= 1` (surname intersection with the OpenAlex record)
- `|year_diff| <= 2`

Statuses: `local` / `searched` (→ resolved universe), `unresolved` (candidates
found, none passed — raw kept), `no_arxiv_id` (not on arXiv — expected for
journal/bioRxiv-only), `search_error` (retryable).

## External-call policy

The **only** network egress is arXiv, paced ≥3s: `api/query` (Stage 0) and
`e-print` (Stage 1). **OpenAlex and Semantic Scholar are forbidden** in this
package. The comparison (Stage 5) runs entirely on local data — the corpus's
in-corpus `edges` field. `compare.py` is built so a third source (S2, or the
candidate pool's `referenced_works`) slots in as another named edge set
without a refactor.

## Acceptance gates (both denominators always reported)

- **coverage** — N of 683 resolved to an arXiv id (local + searched)
- **fetch** — ≥85% of resolved ids source-fetched (rest legitimately `pdf_only`)
- **extract** — ≥90% of source-fetched papers with ≥1 reference

Percentages are always written `X/N (%.1f%%)`; denominators are never averaged
away.
