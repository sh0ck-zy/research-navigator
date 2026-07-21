"""lab/load_graph.py — apply schema.cypher + load the interp corpus into Kùzu.

GATE: schema.cypher is human-verified before this runs.

Populated now (L0):
  • Paper: ingested facts (id, title, abstract, authors, year, venue, cited_by_count)
  • Paper.scores: experimental candidates from ingest_v2 (in_corpus_cites, kw_hits)
  • CITES: real in-corpus citation edges, source='openalex', tagged with run_id
Left NULL until a later stage computes them:
  • Paper.cluster_id / subcluster_id / layout_x / layout_y / centrality / run_id
  • CITES.intent / contexts / confidence   (L3 extraction)
  • SIMILAR.*                                (L2 similarity stage)

Usage:
  python lab/load_graph.py [--reset] [--run-id ingest_v2]
"""
import argparse
import json
from collections import Counter
import shutil
from pathlib import Path

import kuzu

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "raw" / "interp_corpus.jsonl"
DB_PATH = ROOT / "data" / "graph"
SCHEMA = Path(__file__).resolve().parent / "schema.cypher"


def apply_schema(conn):
    """Run schema.cypher — strip // and -- comment lines, execute each statement."""
    lines = [ln for ln in SCHEMA.read_text().splitlines()
             if not ln.strip().startswith(("//", "--"))]
    for stmt in "\n".join(lines).split(";"):
        if stmt.strip():
            conn.execute(stmt)


def load(run_id="ingest_v2", reset=False, corpus=None, db_path=None):
    global CORPUS, DB_PATH
    CORPUS = Path(corpus) if corpus else CORPUS
    DB_PATH = Path(db_path) if db_path else DB_PATH
    papers = [json.loads(ln) for ln in CORPUS.read_text().splitlines() if ln.strip()]
    ids = {p["id"] for p in papers}
    print(f"corpus: {len(papers)} papers, {sum(len(p.get('edges', [])) for p in papers)} in-corpus edges")

    if reset and DB_PATH.exists():
        shutil.rmtree(DB_PATH)
    conn = kuzu.Connection(kuzu.Database(str(DB_PATH)))
    apply_schema(conn)
    print("schema applied from", SCHEMA.name)

    # ── nodes ──
    # Kùzu reads a Python dict as a STRUCT, so a MAP column must be built via
    # map(keys, values) with two list params. (Read later via element_at(m, k).)
    # Empty map([],[]) is ANY-typed and unresolvable, so skip scores if empty.
    base = ("id:$id, arxiv_id:$arxiv_id, doi:$doi, title:$title, abstract:$abstract, "
            "authors:$authors, year:$year, venue:$venue, cited_by_count:$cbc")
    # optional canonical columns — present once L2 has computed them
    canon = {"cluster_id": "cid", "subcluster_id": "sid",
             "layout_x": "lx", "layout_y": "ly", "centrality": "ctr"}
    for p in papers:
        skeys, svals = [], []
        for k, sk in (("_in_corpus_cites", "in_corpus_cites"), ("_kw_hits", "kw_hits"),
                      ("_interp_score", "interp_score")):
            if p.get(k) is not None:
                skeys.append(sk); svals.append(float(p[k]))
        for sk, v in sorted((p.get("_scores") or {}).items()):
            if v is not None:
                skeys.append(sk); svals.append(float(v))
        params = {
            "id": p["id"], "arxiv_id": p.get("arxiv_id"), "doi": p.get("doi"),
            "title": p.get("title"), "abstract": p.get("abstract"),
            "authors": p.get("authors") or [], "year": p.get("year"),
            "venue": p.get("venue"), "cbc": p.get("cited_by_count") or 0,
        }
        props = base
        for col, pn in canon.items():
            if p.get(col) is not None:
                props += f", {col}:${pn}"
                params[pn] = p[col]
        if any(p.get(c) is not None for c in canon):
            props += ", run_id:$run"; params["run"] = run_id
        if skeys:
            params["skeys"], params["svals"] = skeys, svals
            props += ", scores: map($skeys, $svals)"
        conn.execute(f"CREATE (p:Paper {{{props}}})", parameters=params)

    # ── edges (already filtered to in-corpus targets by ingest_v2) ──
    # CITES.source is per-EDGE, not per-run: an edge can come from OpenAlex or from
    # the S2 supplement. `_edge_source` maps target id -> provider; anything not
    # listed predates the S2 supplement and is OpenAlex.
    n_edges = 0
    src_counts = Counter()
    for p in papers:
        esrc = p.get("_edge_source") or {}
        for tgt in p.get("edges", []):
            if tgt in ids:
                src = esrc.get(tgt, "openalex")
                conn.execute(
                    "MATCH (a:Paper {id:$a}), (b:Paper {id:$b}) "
                    "CREATE (a)-[:CITES {source:$src, run_id:$run}]->(b)",
                    parameters={"a": p["id"], "b": tgt, "src": src, "run": run_id},
                )
                n_edges += 1
                src_counts[src] += 1
    print(f"CITES by source: {dict(src_counts)}")

    # ── SIMILAR edges (L2 similarity stage; absent until run_l2 has run) ──
    n_sim = 0
    for p in papers:
        for s in p.get("_similar", []):
            if s["target"] in ids:
                conn.execute(
                    "MATCH (a:Paper {id:$a}), (b:Paper {id:$b}) "
                    "CREATE (a)-[:SIMILAR {weight:$w, metric:$m, model:$mo, run_id:$run}]->(b)",
                    parameters={"a": p["id"], "b": s["target"], "w": float(s["weight"]),
                                "m": s.get("metric", "cosine_knn"),
                                "mo": s.get("model", "all-MiniLM-L6-v2"), "run": run_id},
                )
                n_sim += 1

    n_nodes = conn.execute("MATCH (p:Paper) RETURN count(*)").get_next()[0]
    n_cites = conn.execute("MATCH (:Paper)-[:CITES]->(:Paper) RETURN count(*)").get_next()[0]
    print(f"loaded → {n_nodes} Paper nodes, {n_cites} CITES, {n_sim} SIMILAR  (db: {DB_PATH})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="ingest_v2")
    ap.add_argument("--reset", action="store_true", help="wipe the db dir first")
    ap.add_argument("--corpus", default=None)
    ap.add_argument("--db", default=None)
    args = ap.parse_args()
    load(run_id=args.run_id, reset=args.reset, corpus=args.corpus, db_path=args.db)
