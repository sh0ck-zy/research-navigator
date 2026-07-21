"""lab/hygiene.py — corpus hygiene between capture (ingest_v3) and filtering.

ingest_v3 captures; this stage cleans. Kept separate so it is swappable and so
every removal is auditable: nothing is dropped silently, everything goes to
lab/eval/quarantine.json with a reason.

Stages:
  1. arXiv text repair — OpenAlex silently corrupts title/abstract on some
     records (citation edges and authors survive). For every record with an
     arXiv id we compare OpenAlex's title against arXiv's; on mismatch we take
     title+abstract from arXiv. OpenAlex stays the source of citation edges.
  2. quarantine: corrupt metadata — records still unusable after repair
     ('Untitled', Dagstuhl/DROPS container records). These act as reference
     magnets: OpenAlex mis-resolves hundreds of references onto them, so they
     top the in-degree ranking with nonsense text.
  3. quarantine: reference magnets — high in-pool in-degree, huge global
     citation count, no reference list, non-arXiv venue.
  4. quarantine: single-seed forward expansion — papers whose ONLY link to the
     seed set is citing one designated seed (the sentiment-neuron paper pulls in
     a sentiment-analysis / text-generation tail that is not interp).
  5. dedup — OpenAlex stores preprint and published versions as separate works.
     Merge by normalized title (+/- year window): keep the highest-cited id,
     union the reference lists, and remap every edge in the pool onto it.

Usage:
  python lab/hygiene.py --quarantine-seed 1704.01444
"""
import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CK = ROOT / "data" / "raw" / ".ckpt_v3"
EVAL = ROOT / "lab" / "eval"

ARXIV_API = "http://export.arxiv.org/api/query"
CORRUPT_VENUE = ("DROPS", "Dagstuhl", "Leibniz-Zentrum")


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def clean_arxiv_id(ax):
    if not ax:
        return None
    ax = re.sub(r"v\d+$", "", ax.strip())
    return ax if re.fullmatch(r"\d{4}\.\d{4,5}|[a-z-]+(\.[A-Z]{2})?/\d{7}", ax) else None


def record_arxiv_id(w):
    """arXiv id from the landing page URL, else from the DataCite arXiv DOI.
    The DOI route roughly triples coverage — many arXiv works in OpenAlex have a
    non-arXiv primary_location but still carry 10.48550/arxiv.<id>."""
    ax = clean_arxiv_id(w.get("arxiv_id"))
    if ax:
        return ax
    m = re.match(r"10\.48550/arxiv\.(.+)$", (w.get("doi") or ""), re.I)
    return clean_arxiv_id(m.group(1)) if m else None


def fetch_arxiv(ids, batch=100, pause=3.0):
    """arXiv id -> {'title','abstract'}. Batched; arXiv asks for ~3s between calls."""
    out = {}
    for i in range(0, len(ids), batch):
        chunk = ids[i:i + batch]
        url = f"{ARXIV_API}?" + urllib.parse.urlencode(
            {"id_list": ",".join(chunk), "max_results": len(chunk)})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=90) as r:
                    xml = r.read().decode("utf-8", "replace")
                break
            except Exception as e:
                print(f"  [arxiv] {e}; retry"); time.sleep(5)
        else:
            print(f"  [arxiv] giving up on batch {i//batch}"); continue
        for entry in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
            m = re.search(r"<id>https?://arxiv\.org/abs/([^<]+)</id>", entry)
            t = re.search(r"<title>(.*?)</title>", entry, re.S)
            s = re.search(r"<summary>(.*?)</summary>", entry, re.S)
            if not m:
                continue
            axid = clean_arxiv_id(m.group(1))
            if axid:
                out[axid] = {
                    "title": re.sub(r"\s+", " ", (t.group(1) if t else "")).strip(),
                    "abstract": re.sub(r"\s+", " ", (s.group(1) if s else "")).strip(),
                }
        print(f"  [arxiv] batch {i//batch + 1}/{(len(ids)+batch-1)//batch}: {len(out)} resolved")
        time.sleep(pause)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", default=str(CK / "candidates.json"))
    ap.add_argument("--seeds", default=str(CK / "seeds.json"))
    ap.add_argument("--out", default=str(CK / "candidates_clean.json"))
    ap.add_argument("--quarantine-seed", action="append", default=[],
                    help="arXiv id of a seed whose forward-only citers are quarantined")
    ap.add_argument("--magnet-indeg", type=int, default=50)
    ap.add_argument("--magnet-cbc", type=int, default=3000)
    ap.add_argument("--dedup-year-window", type=int, default=3)
    ap.add_argument("--skip-arxiv", action="store_true")
    args = ap.parse_args()

    works = json.loads(Path(args.candidates).read_text())
    seeds = json.loads(Path(args.seeds).read_text())
    seed_ids = {w["id"] for w in seeds}
    print(f"[hygiene] {len(works)} candidates, {len(seed_ids)} seed records")
    quarantine, audit = [], {}

    def drop(w, reason, detail=""):
        quarantine.append({"id": w["id"], "arxiv_id": w.get("arxiv_id"), "year": w.get("year"),
                           "title": w["title"][:120], "venue": w.get("venue"),
                           "cited_by_count": w.get("cited_by_count"),
                           "reason": reason, "detail": detail})

    # ── 1 · arXiv text repair ────────────────────────────────────────────────
    # arXiv is authoritative for the TEXT of an arXiv paper, so we take title +
    # abstract from it whenever we can resolve one. Detecting corruption by title
    # mismatch alone is not enough: ingest_v3 repairs seed titles from ground
    # truth, which makes the title agree while the ABSTRACT stays corrupt (Toy
    # Models of Superposition is exactly this case). OpenAlex remains the sole
    # source of citation edges.
    repaired = title_changed = 0
    if not args.skip_arxiv:
        by_ax = {}
        for w in works:
            ax = record_arxiv_id(w)
            if ax:
                w["_arxiv_resolved"] = ax
                by_ax.setdefault(ax, []).append(w)
        print(f"[1] arXiv text repair: {len(by_ax)} records resolve to an arXiv id")
        got = fetch_arxiv(sorted(by_ax))
        for ax, rows in by_ax.items():
            ref = got.get(ax)
            if not ref or not ref["title"]:
                continue
            for w in rows:
                a, b = norm(w["title"]), norm(ref["title"])
                if not (a == b or a.startswith(b) or b.startswith(a)):
                    w["_orig_title"] = w["title"]
                    title_changed += 1
                w["title"] = ref["title"]
                if ref["abstract"]:
                    w["abstract"] = ref["abstract"]
                w["_text_source"] = "arxiv"
                repaired += 1
        print(f"[1] took arXiv text for {repaired} records "
              f"({title_changed} had a corrupted/divergent title)")
    audit["arxiv_text_records"] = repaired
    audit["arxiv_title_corrections"] = title_changed

    # ── 2 · quarantine corrupt metadata ──────────────────────────────────────
    keep = []
    for w in works:
        v = w.get("venue") or ""
        if w["title"].strip() in ("Untitled", "") and w["id"] not in seed_ids:
            drop(w, "corrupt_metadata", "title is 'Untitled' after repair")
        elif any(t in v for t in CORRUPT_VENUE) and w["id"] not in seed_ids:
            drop(w, "corrupt_metadata", f"container/corrupt venue: {v[:50]}")
        else:
            keep.append(w)
    print(f"[2] corrupt metadata: {len(works)-len(keep)} quarantined")
    works = keep

    # ── 3 · quarantine reference magnets ─────────────────────────────────────
    pool = {w["id"] for w in works}
    indeg = Counter()
    for w in works:
        for r in w["referenced_works"]:
            if r in pool:
                indeg[r] += 1
    keep = []
    for w in works:
        is_arxiv = "arxiv" in (w.get("venue") or "").lower() or w.get("arxiv_id")
        if (indeg[w["id"]] >= args.magnet_indeg and w["cited_by_count"] >= args.magnet_cbc
                and not w["referenced_works"] and not is_arxiv and w["id"] not in seed_ids):
            drop(w, "reference_magnet",
                 f"indeg={indeg[w['id']]} cbc={w['cited_by_count']} refs=0 venue={w.get('venue')}")
        else:
            keep.append(w)
    print(f"[3] reference magnets: {len(works)-len(keep)} quarantined")
    works = keep

    # ── 4 · quarantine single-seed forward expansion ─────────────────────────
    qseeds = set()
    for ax in args.quarantine_seed:
        for s in seeds:
            if record_arxiv_id(s) == clean_arxiv_id(ax) or norm(ax) in norm(s["title"]):
                qseeds.add(s["id"])
    if qseeds:
        keep = []
        for w in works:
            if w["id"] in seed_ids:
                keep.append(w); continue
            linked = {r for r in w["referenced_works"] if r in seed_ids}
            if linked and linked <= qseeds:
                drop(w, "single_seed_forward",
                     f"only seed link is {sorted(qseeds & linked)}")
            else:
                keep.append(w)
        print(f"[4] single-seed forward ({len(qseeds)} seed record(s)): "
              f"{len(works)-len(keep)} quarantined")
        works = keep
    audit["quarantine_seeds"] = sorted(qseeds)

    # ── 5 · dedup ────────────────────────────────────────────────────────────
    groups = defaultdict(list)
    for w in works:
        groups[norm(w["title"])].append(w)
    canonical, remap, merged = [], {}, 0
    for key, rows in groups.items():
        if len(rows) == 1:
            canonical.append(rows[0]); continue
        rows.sort(key=lambda w: (-(w.get("cited_by_count") or 0), w["id"]))
        head = rows[0]
        base_year = head.get("year") or 0
        same, other = [head], []
        for w in rows[1:]:
            if abs((w.get("year") or base_year) - base_year) <= args.dedup_year_window:
                same.append(w)
            else:
                other.append(w)
        refs = set(head["referenced_works"])
        for w in same[1:]:
            refs |= set(w["referenced_works"])
            remap[w["id"]] = head["id"]
            if not head.get("abstract") and w.get("abstract"):
                head["abstract"] = w["abstract"]
            head["cited_by_count"] = max(head["cited_by_count"] or 0, w["cited_by_count"] or 0)
            merged += 1
            drop(w, "duplicate", f"merged into {head['id']} ({head['title'][:60]})")
        head["referenced_works"] = sorted(refs)
        head["_merged_versions"] = len(same)
        canonical.append(head)
        canonical.extend(other)
    # remap every edge in the pool onto the canonical ids
    ids = {w["id"] for w in canonical}
    for w in canonical:
        w["referenced_works"] = sorted({remap.get(r, r) for r in w["referenced_works"]} - {w["id"]})
    print(f"[5] dedup: {merged} duplicate records merged into {len(groups)} title groups")
    audit["duplicates_merged"] = merged

    works = canonical
    n_edges = sum(1 for w in works for r in w["referenced_works"] if r in ids)
    audit.update(kept=len(works), quarantined=len(quarantine), in_pool_edges=n_edges,
                 by_reason=dict(Counter(q["reason"] for q in quarantine)))
    Path(args.out).write_text(json.dumps(works))
    (EVAL / "quarantine.json").write_text(json.dumps(
        {"audit": audit, "quarantined": quarantine}, indent=2))
    print(f"\n[hygiene] kept {len(works)} | quarantined {len(quarantine)} "
          f"{audit['by_reason']} | in-pool edges {n_edges}")
    print(f"→ {args.out}\n→ {EVAL / 'quarantine.json'}")


if __name__ == "__main__":
    main()
