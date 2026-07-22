"""lab/latex_refs/common.py — shared plumbing for the LaTeX-refs citation index.

This workstream builds our OWN citation index from arXiv LaTeX e-print source,
parallel to (and never touching) the frozen Kùzu graph / clustering / layout.
The point is the informal citation layer no aggregator captures: web-pub URLs
(transformer-circuits.pub, distill.pub) and arXiv refs sitting in \\bibitem /
.bbl / .bib entries.

Everything here is source-agnostic infrastructure:
  - the corpus loader + the LOCAL arXiv-id extractor (fields only, no network)
  - normalization + verification helpers (title / author / year) shared by the
    id-resolution gate and the ref-resolution stage
  - the per-paper checkpoint contract: every stage writes one JSON per paper
    under data/latex/ckpt/<stage>/<Wid>.json so a crash at paper 400 resumes at
    401, then aggregates into a single tracked data/latex/<stage>.jsonl.

No stage in this package writes to the main graph, calls OpenAlex or S2, or
touches ingest_v3 / eval assets. The only network egress is arXiv, paced 3s,
and it lives in resolve_ids.py (api/query) and fetch_sources.py (e-print).
"""
import json
import re
import unicodedata
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parent.parent.parent
CORPUS = ROOT / "data" / "raw" / "interp_corpus_v3_clean.jsonl"
POOL_CLEAN = ROOT / "data" / "raw" / ".ckpt_v3" / "candidates_clean.json"
POOL_RAW = ROOT / "data" / "raw" / ".ckpt_v3" / "candidates.json"

LATEX = ROOT / "data" / "latex"
SOURCES = LATEX / "sources"
CKPT = LATEX / "ckpt"
EVAL = ROOT / "lab" / "eval"
# Frozen canonical clustering (hybrid a0.25). Read-only here — this package
# never writes clustering; it only cross-tabs coverage against it for reporting.
VIEWER = ROOT / "lab" / "out" / "viewer_data.json"

# arXiv new-style (2202.05262) and old-style (hep-th/9901001) identifiers.
ARXIV_NEW = r"\d{4}\.\d{4,5}"
ARXIV_OLD = r"[a-z-]+(?:\.[A-Z]{2})?/\d{7}"
ARXIV_RE = re.compile(rf"({ARXIV_NEW}|{ARXIV_OLD})")

# Web-native publication hosts whose citations no DOI/OpenAlex index captures —
# the whole reason this workstream exists. Kept as (label, regex) so compare.py
# can bucket by venue.
WEBPUB_HOSTS = [
    ("transformer-circuits", re.compile(r"transformer-circuits\.pub", re.I)),
    ("distill", re.compile(r"distill\.pub", re.I)),
    ("colah", re.compile(r"colah\.github\.io", re.I)),
    ("openai-blog", re.compile(r"openai\.com/(?:research|blog|index)", re.I)),
    ("anthropic", re.compile(r"anthropic\.com/(?:research|news)", re.I)),
    ("neelnanda", re.compile(r"neelnanda\.io", re.I)),
    ("lesswrong", re.compile(r"lesswrong\.com", re.I)),
    ("alignmentforum", re.compile(r"alignmentforum\.org", re.I)),
]


def _fold(s):
    """NFKD-decompose and drop combining marks so 'Marín' folds to 'Marin'.
    Without this, the accented surname never intersects the un-accented copy in
    the OpenAlex record and a real match is wrongly rejected by the author gate."""
    return "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c))


def norm(s):
    """Lowercase, strip diacritics, collapse non-alphanumerics to single spaces."""
    return re.sub(r"[^a-z0-9]+", " ", _fold(s).lower()).strip()


_ACCENT_RE = re.compile(r'\\[\"\'`^~=.]\s*\{?\s*([A-Za-z])\}?')
_CMD_ARG_RE = re.compile(r'\\[A-Za-z]+\*?\s*\{([^{}]*)\}')
_CMD_RE = re.compile(r'\\[A-Za-z]+\*?')


def delatex(s):
    """Flatten LaTeX to plain-ish text: drop \\newblock, unwrap one-arg text
    commands (\\emph{X} -> X), fold accents (\\\"{u} -> u), strip the rest.
    Best-effort — enough for title matching and readable audit, not a TeX engine."""
    if not s:
        return ""
    s = s.replace("\\newblock", " ").replace("~", " ")
    s = _ACCENT_RE.sub(r"\1", s)          # \"{u} \'e \`o \~n -> base letter
    for _ in range(3):                    # unwrap nested \emph{\textbf{X}}
        s = _CMD_ARG_RE.sub(r"\1", s)
    s = _CMD_RE.sub(" ", s)               # remaining bare commands
    s = re.sub(r"\\([&_%#$])", r"\1", s)  # escaped specials
    # Braces -> EMPTY, not space: '{C}lever {H}ans' must yield 'Clever Hans',
    # not 'C lever H ans' (brace->space split tokens and sank title matches).
    # Code-level fix only — refs.jsonl/contexts.jsonl NOT re-run for it yet;
    # see README backlog ("full refresh pending").
    s = s.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", s).strip()


def clean_arxiv(ax):
    """Strip version suffix and validate; return canonical id or None."""
    if not ax:
        return None
    ax = str(ax).strip()
    ax = re.sub(r"^arxiv:", "", ax, flags=re.I)
    ax = re.sub(r"v\d+$", "", ax)
    return ax if re.fullmatch(rf"{ARXIV_NEW}|{ARXIV_OLD}", ax) else None


def local_arxiv_id(rec):
    """arXiv id from LOCAL fields only (no network): arxiv_id, _arxiv_resolved,
    then an arxiv-encoding DOI (10.48550/arxiv.XXXX). Returns None if the record
    carries no local arXiv linkage — those go to the title-search gate."""
    for f in ("arxiv_id", "_arxiv_resolved"):
        c = clean_arxiv(rec.get(f))
        if c:
            return c
    m = re.search(rf"arxiv\.({ARXIV_NEW}|{ARXIV_OLD})", (rec.get("doi") or "").lower())
    return clean_arxiv(m.group(1)) if m else None


def surnames(authors):
    """Lowercased surname set from author strings. Handles both arXiv's
    'First Last' and the corpus's 'Surname, Initials' format: a comma means
    the surname is the pre-comma part (else last token). 'Harris, CR' -> harris,
    not the initials 'cr' — the bug that silently zeroed the author gate."""
    out = set()
    for a in authors or []:
        name = a.split(",", 1)[0] if "," in a else a
        toks = norm(name).split()
        if toks:
            out.add(toks[-1])
    return out


def title_sim(a, b):
    """rapidfuzz token_set_ratio on normalized titles, scaled to 0..1."""
    return fuzz.token_set_ratio(norm(a), norm(b)) / 100.0


def load_corpus():
    """The 683 interp corpus records (the citing set). Keyed by OpenAlex id."""
    return [json.loads(line) for line in CORPUS.open() if line.strip()]


def oa_key(rec_or_id):
    """Bare OpenAlex id (W...) — the stable per-paper key across all stages."""
    v = rec_or_id["id"] if isinstance(rec_or_id, dict) else rec_or_id
    return str(v).split("/")[-1]


# ---- checkpoint contract ---------------------------------------------------

def ckpt_path(stage, wid):
    return CKPT / stage / f"{wid}.json"


def load_ckpt(stage, wid):
    p = ckpt_path(stage, wid)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except json.JSONDecodeError:
            return None  # partial/corrupt write — reprocess
    return None


def save_ckpt(stage, wid, obj):
    p = ckpt_path(stage, wid)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False))
    tmp.replace(p)  # atomic: a crash mid-write never leaves a half file at p


def aggregate(stage, out_name):
    """Fold every per-paper checkpoint for a stage into one tracked jsonl.
    Returns the list of records written."""
    recs = []
    d = CKPT / stage
    if d.exists():
        for p in sorted(d.glob("*.json")):
            try:
                recs.append(json.loads(p.read_text()))
            except json.JSONDecodeError:
                continue
    out = LATEX / out_name
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return recs


def pct(n, d):
    """Format 'n/d (xx.x%)' — denominators are always shown, never averaged."""
    return f"{n}/{d} ({100 * n / d:.1f}%)" if d else f"{n}/0 (n/a)"


# ---- coverage x cluster cross-tab (read-only against the frozen partition) --

def load_cluster_map():
    """{Wid: (cluster_id, name)} from the frozen hybrid-a0.25 partition. Read-only.
    Returns {} if the viewer data isn't present, so reports degrade gracefully."""
    if not VIEWER.exists():
        return {}
    d = json.loads(VIEWER.read_text())
    names = {c["id"]: c["name"] for c in d.get("clusters", [])}
    return {p["id"].split("/")[-1]: (p["cluster_id"], names.get(p["cluster_id"], "?"))
            for p in d.get("papers", [])}


def print_status_by_cluster(recs, id_key, status_key, target, header):
    """Cross-tab one status against the frozen clusters: is a miss concentrated
    (expected journal/bioRxiv clusters) or spread (a resolution gap)? Prints the
    target count / cluster total per cluster, both denominators, descending by
    miss count. No-op if the cluster map is unavailable."""
    from collections import Counter, defaultdict
    cmap = load_cluster_map()
    if not cmap:
        return
    per = defaultdict(Counter)
    for r in recs:
        cid, name = cmap.get(r[id_key], (None, "(unmapped)"))
        per[(cid, name)]["t"] += 1
        if r[status_key] == target:
            per[(cid, name)]["hit"] += 1
    print(f"  {header}")
    for (cid, name), c in sorted(per.items(), key=lambda kv: -kv[1]["hit"]):
        if c["hit"]:
            print(f"    [{cid}] {(name or '?')[:34]:34s} {pct(c['hit'], c['t'])}")
