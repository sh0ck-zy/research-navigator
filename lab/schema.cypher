// lab/schema.cypher — The Knowledge Lab graph (Kùzu)
//
// Design rules (locked with Joao):
//   • Fixed columns for singular/canonical results (cluster_id, subcluster_id,
//     layout_x/y, centrality = the official blend).
//   • scores MAP(STRING,DOUBLE) holds experimental metric CANDIDATES
//     (in_corpus_cites, pagerank, betweenness, ...) — they never touch the schema.
//   • run_id STRING tags every experiment run on all three tables: the MAP says
//     WHICH metric, run_id says WHICH run; the canonical freeze records its run.
//   • Rel tables are RICH from day one (never bare) — props nullable, populated
//     later (CITES.intent/contexts/confidence at L3) so the graph grows toward a
//     typed KG (Method/Dataset/Claim) with no migration.

CREATE NODE TABLE Paper(
    // ── ingested facts (ingest_v2 → OpenAlex) ──
    id              STRING,
    arxiv_id        STRING,
    doi             STRING,
    title           STRING,
    abstract        STRING,
    authors         STRING[],
    year            INT64,
    venue           STRING,
    cited_by_count  INT64,
    // ── singular canonical results (NULL until a stage computes + freezes them) ──
    cluster_id      INT64,
    subcluster_id   INT64,
    layout_x        DOUBLE,
    layout_y        DOUBLE,
    centrality      DOUBLE,               // the OFFICIAL blend
    // ── experimental metric candidates, schema-free ──
    scores          MAP(STRING, DOUBLE),  // e.g. in_corpus_cites, kw_hits, pagerank, ...
    // ── provenance: which run froze the canonical values above ──
    run_id          STRING,
    PRIMARY KEY (id)
);

CREATE REL TABLE CITES(
    FROM Paper TO Paper,
    intent      STRING,     // L3: uses | extends | compares | background | contradicts
    contexts    STRING[],   // L3: verbatim citing sentences (grounding)
    confidence  DOUBLE,     // L3
    source      STRING,     // 'openalex' | 's2'  (populated at load)
    run_id      STRING
);

CREATE REL TABLE SIMILAR(
    FROM Paper TO Paper,
    weight  DOUBLE,         // similarity score (populated by the similarity stage)
    metric  STRING,         // 'cosine' | ...
    model   STRING,         // 'all-MiniLM-L6-v2' | 'specter2' | ...
    run_id  STRING
);
