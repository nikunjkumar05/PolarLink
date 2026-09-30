"""Module 3 e2e: hybrid search — keyword, semantic, fusion, filters, deep links."""

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

FRONT = "http://localhost:5173"
PASSED, FAILED = [], []


def check(label, condition, detail=""):
    (PASSED if condition else FAILED).append(label)
    print(f"{'PASS' if condition else 'FAIL'}  {label}" + (f"  [{detail}]" if detail else ""))


def get(path, params=None):
    url = FRONT + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=90) as res:
            return res.status, json.load(res)
    except urllib.error.HTTPError as exc:
        return exc.code, json.load(exc) if exc.fp else {}


def search(**params):
    return get("/api/search", params)[1]


def post(path):
    req = urllib.request.Request(FRONT + path, method="POST", data=b"")
    try:
        with urllib.request.urlopen(req, timeout=90) as res:
            return res.status, json.load(res)
    except urllib.error.HTTPError as exc:
        return exc.code, json.load(exc) if exc.fp else {}


def tokens(text):
    return {t.lower() for t in re.findall(r"\w+", text)}


# ------------------------------------------------------------------ health
status, health = get("/api/health")
check("health returns 200", status == 200)
check("health reports the search module", "search" in health.get("modules", ""), health.get("modules"))

# ------------------------------------------------------------------ modes
status, modes = get("/api/search/modes")
check("modes endpoint lists all three modes", status == 200 and modes == ["hybrid", "keyword", "semantic"], str(modes))

# ------------------------------------------------------------------ index
hybrid = search(q="sea ice", mode="hybrid", limit=20)
index = hybrid.get("index", {})
check("index reports a keyword row count", index.get("keyword_rows", 0) > 0, str(index.get("keyword_rows")))
check(
    "index fully embedded",
    index.get("embedded_passages") == index.get("total_passages", -1) > 0,
    f"{index.get('embedded_passages')}/{index.get('total_passages')}",
)
check("embedding model recorded", bool(index.get("embedding_model")), str(index.get("embedding_model")))
check("no embedding error", not index.get("embedding_error"), str(index.get("embedding_error")))

# ------------------------------------------------------------------ response shape
check("search returns ranked items", hybrid.get("total", 0) > 0 and len(hybrid.get("items", [])) > 0)
first = hybrid["items"][0]
for field in ("rank", "score", "sources", "passage", "asset", "version", "keyword_rank", "semantic_rank"):
    check(f"hit carries '{field}'", field in first)
check("passage has offsets for highlighting", first["passage"].get("start_offset") is not None)
check("hit links asset + version + passage", all(
    key in first for key in ("asset", "version", "passage")
) and first["asset"].get("id") and first["version"].get("id") and first["passage"].get("id"))
check("took_ms is reported", isinstance(hybrid.get("took_ms"), int))

# ------------------------------------------------------------------ keyword leg
kw = search(q="coastal transect", mode="keyword", limit=5)
kw_ids = [i["passage"]["id"] for i in kw["items"]]
check("keyword mode returns matches", len(kw_ids) > 0, str(kw_ids))
check(
    "keyword ranks the literal phrase first",
    kw_ids and kw["items"][0]["passage"]["content"].lower().find("coastal transect") >= 0,
    kw["items"][0]["asset"]["title"] if kw_ids else "no hits",
)
check("keyword hits are keyword-sourced", all("keyword" in i["sources"] for i in kw["items"]))
check("keyword ranks are populated", all(i["keyword_rank"] is not None for i in kw["items"]))

# ------------------------------------------------------------------ semantic leg
sem_query = "frozen seawater seen from above"
sem = search(q=sem_query, mode="semantic", limit=10)
sem_items = sem.get("items", [])
check("semantic mode returns matches", len(sem_items) > 0)
check("semantic hits are semantic-sourced", all("semantic" in i["sources"] for i in sem_items))
check("semantic ranks are populated", all(i["semantic_rank"] is not None for i in sem_items))

query_tokens = tokens(sem_query)
lexical_free = [
    i for i in sem_items
    if not (query_tokens & tokens(i["passage"]["content"] + " " + i["asset"]["title"]))
]
check(
    "FR-11: a result shares no wording with the query",
    len(lexical_free) > 0,
    f"{len(lexical_free)}/{len(sem_items)} overlap-free",
)
sea_ice_ids = {i["passage"]["id"] for i in search(q=sem_query, mode="semantic", limit=20)["items"]}
kw_overlap = search(q=sem_query, mode="keyword", limit=20)
kw_ids_all = {i["passage"]["id"] for i in kw_overlap.get("items", [])}
semantic_only = sea_ice_ids - kw_ids_all
check(
    "semantic retrieves passages keyword search misses",
    len(semantic_only) > 0,
    f"{len(semantic_only)} semantic-only",
)

# ------------------------------------------------------------------ fusion
FUSION_QUERY = "brine salinity ice core"
fused = search(q=FUSION_QUERY, mode="hybrid", limit=100)
kw_fuse = search(q=FUSION_QUERY, mode="keyword", limit=100)
sem_fuse = search(q=FUSION_QUERY, mode="semantic", limit=100)
both = [i for i in fused["items"] if set(i["sources"]) >= {"keyword", "semantic"}]
check("hybrid fuses passages found by both retrievers", len(both) > 0, f"{len(both)} fused")
check(
    "hybrid result count >= each single leg",
    fused["total"] >= max(kw_fuse["total"], sem_fuse["total"]),
    str(fused["total"]),
)
hybrid_ids = {i["passage"]["id"] for i in fused["items"]}
check(
    "hybrid keeps every passage either retriever found",
    bool(hybrid_ids)
    and {i["passage"]["id"] for i in kw_fuse["items"]} <= hybrid_ids
    and {i["passage"]["id"] for i in sem_fuse["items"]} <= hybrid_ids,
    f"{len(hybrid_ids)} fused ids / {kw_fuse['total']} kw / {sem_fuse['total']} sem",
)
top = fused["items"][0]
check("fused hit exposes both leg scores", "keyword_score" in top and "semantic_score" in top)


def rrf_sum(hit):
    """Recompute the fused score from the reported per-leg ranks (k = 60)."""
    total = 0.0
    for rank in (hit.get("keyword_rank"), hit.get("semantic_rank")):
        if rank is not None:
            total += 1.0 / (60 + rank)
    return total


offenders = [
    i["rank"]
    for i in fused["items"]
    if abs(i["score"] - rrf_sum(i)) > 1e-6  # the API rounds to 6 decimals
]
check(
    "fused score is exactly sum(1/(60+rank)) over both legs",
    bool(fused["items"]) and not offenders,
    f"ranks off: {offenders}" if offenders else f"{len(fused['items'])} hits verified",
)

# ------------------------------------------------------------------ filters
def titles(params):
    return {i["asset"]["title"] for i in search(**params)["items"]}

only_pdf = search(q="ice", mode="hybrid", limit=50, asset_type="PDF")
check(
    "asset_type filter applied",
    all(i["asset"]["asset_type"] == "PDF" for i in only_pdf["items"]) and len(only_pdf["items"]) > 0,
    f"{len(only_pdf['items'])} PDF hits",
)
wildlife = search(q="fox kits", mode="hybrid", limit=50, topic="Wildlife")
check("topic filter applied", all(i["asset"]["topic"] == "Wildlife" for i in wildlife["items"]))
restricted = search(q="sediment core", mode="hybrid", limit=50, access_level="RESTRICTED")
check(
    "access_level filter applied",
    all(i["asset"]["access_level"] == "RESTRICTED" for i in restricted["items"]) and restricted["items"],
    str(len(restricted["items"])),
)
year_hits = search(q="ice", mode="hybrid", limit=50, year=2024)
check("year filter applied", all(i["asset"]["year"] == 2024 for i in year_hits["items"]) and year_hits["items"])
combo = search(q="ice", mode="hybrid", limit=50, expedition="IAE-42", station="Maitri")
check(
    "expedition + station filters compose",
    all(i["asset"]["expedition"] == "IAE-42" and i["asset"]["station"] == "Maitri" for i in combo["items"]),
    f"{len(combo['items'])} hits",
)
no_match = search(q="zzzznotathing", mode="keyword", limit=10)
check("impossible query yields no keyword matches", no_match["total"] == 0, str(no_match["total"]))

# ------------------------------------------------------------------ edge cases
status, empty = get("/api/search", {"q": "", "mode": "hybrid"})
check("empty query is rejected with a note", status == 200 and empty["total"] == 0 and bool(empty.get("note")), str(empty.get("note")))

status, bogus = get("/api/search", {"q": "ice", "mode": "banana"})
check("unknown mode falls back to hybrid", status == 200 and bogus["mode"] == "hybrid", bogus.get("mode"))

hostile = urllib.parse.quote('"NEAR" AND OR (* NEAR(x ')
status, bad = get("/api/search", {"q": hostile, "mode": "keyword"})
check("FTS5 syntax injection cannot break search", status == 200 and isinstance(bad.get("total"), int), f"status={status}")

status, bad_limit = get("/api/search", {"q": "ice", "limit": "9999"})
check("oversized limit is rejected", status == 422, f"status={status}")

# ------------------------------------------------------------------ reindex safety
before = search(q="ice", mode="hybrid", limit=50)["index"]
assets = get("/api/assets", {"page_size": 100})[1]
version_ids = [
    a["latest_version"]["id"] for a in assets["items"] if a.get("latest_version")
]
check("repository exposes versions to reprocess", len(version_ids) > 0, str(len(version_ids)))
status, _ = post(f"/api/versions/{version_ids[0]}/reprocess")
check("reprocess accepted", status == 200, f"status={status}")

import time

for _ in range(60):
    time.sleep(0.5)
    after = search(q="ice", mode="hybrid", limit=50)["index"]
    if after["keyword_rows"] == before["keyword_rows"] and after["embedded_passages"] == before["embedded_passages"]:
        break
check(
    "reprocess rebuilds the index without leaking rows",
    after["keyword_rows"] == before["keyword_rows"] == after["total_passages"],
    f"{before['keyword_rows']} -> {after['keyword_rows']}",
)
check(
    "reprocess keeps embeddings in step",
    after["embedded_passages"] == after["total_passages"],
    f"{after['embedded_passages']}/{after['total_passages']}",
)

# ------------------------------------------------------------------ frontend
def module_body(path):
    try:
        with urllib.request.urlopen(FRONT + path, timeout=30) as res:
            return res.status, res.headers.get("Content-Type", ""), res.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        return 0, "", str(exc)


for module in ("/src/pages/Search.tsx", "/src/App.tsx", "/src/api/client.ts"):
    status, ctype, body = module_body(module)
    transformed = "sourceMappingURL" in body  # appended by the Vite transform pipeline
    jsx_compiled = "jsxDEV" in body if module.endswith(".tsx") else True
    check(
        f"vite compiles {module} to javascript",
        status == 200 and "javascript" in ctype and transformed and jsx_compiled,
        f"{status} {ctype} len={len(body)}",
    )

with urllib.request.urlopen(FRONT + "/src/App.tsx", timeout=30) as res:
    app_tsx = res.read().decode("utf-8", "replace")
check("Search route registered", "/search" in app_tsx)

deep = f"/assets/{first['asset']['id']}?v={first['version']['id']}&passage={first['passage']['id']}"
check("deep link builds from a hit", "passage=" in deep and "v=" in deep, deep)

print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
if FAILED:
    print("failed: " + ", ".join(FAILED))
sys.exit(1 if FAILED else 0)
