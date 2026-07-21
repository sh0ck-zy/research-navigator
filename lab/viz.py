"""lab/viz.py — dev viewer over the Kùzu graph (NOT the product galaxy).

Renders two HTML artifacts into lab/out/ so you can *see* the graph while
iterating:
  scatter.html — plotly 2D scatter; position = canonical layout_x/y if present,
                 else an on-the-fly Fruchterman-Reingold layout; color = cluster_id
                 if present, else on-the-fly community (Louvain); size ~ in-corpus cites.
  graph.html   — pyvis interactive citation graph (whole corpus, or one paper's
                 neighborhood with --focus <id> --hops N).

Works at every stage: with only CITES loaded (plumbing) it derives layout +
communities from the citation graph; once L2 fills layout_x/y + cluster_id it
uses those instead.

Usage:
  python lab/viz.py                       # whole graph
  python lab/viz.py --focus <paper_id> --hops 1
"""
import argparse
from pathlib import Path

import igraph as ig
import kuzu
import plotly.graph_objects as go
from pyvis.network import Network

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)
PREFIX = ""
DB = str(ROOT / "data" / "graph")


def fetch(conn):
    papers = {}
    r = conn.execute(
        "MATCH (p:Paper) RETURN p.id, p.title, p.year, p.cluster_id, "
        "p.layout_x, p.layout_y, element_at(p.scores,'in_corpus_cites')[1]"
    )
    while r.has_next():
        pid, title, year, cid, x, y, icc = r.get_next()
        papers[pid] = {"title": title or "?", "year": year, "cluster": cid,
                       "x": x, "y": y, "icc": icc or 0.0}
    edges = []
    r = conn.execute("MATCH (a:Paper)-[:CITES]->(b:Paper) RETURN a.id, b.id")
    while r.has_next():
        a, b = r.get_next()
        edges.append((a, b))
    return papers, edges


def derive(papers, edges):
    """Fill missing layout + cluster from the citation graph (plumbing stage)."""
    ids = list(papers)
    idx = {p: i for i, p in enumerate(ids)}
    g = ig.Graph(n=len(ids), directed=False,
                 edges=[(idx[a], idx[b]) for a, b in edges if a in idx and b in idx])
    if any(papers[p]["x"] is None for p in ids):
        lay = g.layout_fruchterman_reingold()
        for p, i in idx.items():
            if papers[p]["x"] is None:
                papers[p]["x"], papers[p]["y"] = lay[i][0], lay[i][1]
    if all(papers[p]["cluster"] is None for p in ids):
        comm = g.community_multilevel()
        for ci, members in enumerate(comm):
            for m in members:
                papers[ids[m]]["cluster"] = ci
    return papers


def make_scatter(papers):
    xs = [p["x"] for p in papers.values()]
    ys = [p["y"] for p in papers.values()]
    cs = [p["cluster"] if p["cluster"] is not None else -1 for p in papers.values()]
    sizes = [6 + 2.2 * (p["icc"] or 0) ** 0.5 for p in papers.values()]
    text = [f"{p['title'][:80]} ({p['year']})<br>in-corpus cites: {int(p['icc'] or 0)} · cluster {c}"
            for p, c in zip(papers.values(), cs)]
    fig = go.Figure(go.Scatter(
        x=xs, y=ys, mode="markers", text=text, hoverinfo="text",
        marker=dict(size=sizes, color=cs, colorscale="Turbo", showscale=False,
                    line=dict(width=0.3, color="rgba(0,0,0,0.3)"), opacity=0.85)))
    fig.update_layout(template="plotly_dark", title="Knowledge Lab — dev scatter",
                      xaxis=dict(visible=False), yaxis=dict(visible=False),
                      margin=dict(l=0, r=0, t=40, b=0))
    out = OUT / f"{PREFIX}scatter.html"
    fig.write_html(str(out))
    return out


def make_graph(papers, edges, focus=None, hops=1):
    keep = set(papers)
    if focus:
        keep, frontier = {focus}, {focus}
        adj = {}
        for a, b in edges:
            adj.setdefault(a, set()).add(b)
            adj.setdefault(b, set()).add(a)
        for _ in range(hops):
            nxt = set()
            for n in frontier:
                nxt |= adj.get(n, set())
            keep |= nxt
            frontier = nxt
    net = Network(height="800px", width="100%", bgcolor="#0a0a0a",
                  font_color="#ddd", directed=True)
    net.barnes_hut()
    for pid in keep:
        p = papers[pid]
        net.add_node(pid, label=(p["title"][:40]), title=p["title"],
                     group=p["cluster"], value=1 + (p["icc"] or 0))
    for a, b in edges:
        if a in keep and b in keep:
            net.add_edge(a, b)
    out = OUT / (f"{PREFIX}graph.html" if not focus else f"{PREFIX}graph_{focus}.html")
    net.write_html(str(out), notebook=False)
    return out, len(keep)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--focus", default=None)
    ap.add_argument("--hops", type=int, default=1)
    ap.add_argument("--db", default=DB)
    ap.add_argument("--prefix", default="")
    args = ap.parse_args()
    global PREFIX
    PREFIX = args.prefix
    conn = kuzu.Connection(kuzu.Database(args.db))
    papers, edges = fetch(conn)
    papers = derive(papers, edges)
    s = make_scatter(papers)
    g, n = make_graph(papers, edges, args.focus, args.hops)
    print(f"scatter → {s}  ({len(papers)} papers)")
    print(f"graph   → {g}  ({n} nodes, {len(edges)} edges shown)")


if __name__ == "__main__":
    main()
