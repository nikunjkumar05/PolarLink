import json
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE = "http://localhost:5173"

PDF = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj
xref
0 4
0000000000 65535 f
trailer<</Root 1 0 R/Size 4>>
startxref
0
%%EOF
"""


def multipart(url, fields, filename, content, token=None):
    boundary = uuid.uuid4().hex
    body = b""
    for key, value in fields.items():
        body += (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n"
        ).encode()
    body += (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode()
    body += content + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        BASE + url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def get(path, raw=False):
    req = urllib.request.Request(BASE + path)
    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            return resp.status, (data if raw else json.loads(data))
    except urllib.error.HTTPError as exc:
        data = exc.read()
        try:
            data = json.loads(data)
        except Exception:
            pass
        return exc.code, data


def main():
    checks = []

    def check(name, ok, extra=""):
        checks.append(ok)
        print(f"{'PASS' if ok else 'FAIL'}  {name}{(' — ' + str(extra)) if extra else ''}")

    status, health = get("/api/health")
    check("health via proxy", status == 200 and "document-processing" in health.get("modules", ""), health)

    status, created = multipart(
        "/api/assets",
        {
            "meta": json.dumps(
                {
                    "title": "42nd Indian Antarctic Expedition Report",
                    "description": "Season summary covering Maitri station operations.",
                    "asset_type": "PDF",
                    "topic": "Antarctica",
                    "expedition": "IAE-42",
                    "station": "Maitri",
                    "year": 2025,
                    "author": "NCPOR",
                    "keywords": "sea ice, expedition, glacier",
                    "attribution": "(c) NCPOR, MoES",
                    "access_level": "PUBLIC",
                    "note": "Initial submission",
                }
            )
        },
        "IAE42_report.pdf",
        PDF,
    )
    check("upload asset", status == 201 and created["version_count"] == 1, f"{status}")
    asset_id = created["id"]

    status, listed = get("/api/assets?q=antarctic")
    check(
        "keyword search",
        status == 200
        and listed["total"] >= 1
        and any(item["id"] == asset_id for item in listed["items"]),
        listed["total"],
    )

    status, filtered = get("/api/assets?year=2025&asset_type=PDF&station=Maitri")
    check(
        "facet filters",
        status == 200
        and any(item["id"] == asset_id for item in filtered["items"])
        and all(
            item["year"] == 2025
            and item["asset_type"] == "PDF"
            and item["station"] == "Maitri"
            for item in filtered["items"]
        ),
        filtered["total"],
    )

    status, miss = get("/api/assets?year=1999")
    check("non-matching filter", status == 200 and miss["total"] == 0, miss["total"])

    status, detail = get(f"/api/assets/{asset_id}")
    for _ in range(60):
        if detail["versions"][0]["processing_status"] in ("DONE", "FAILED"):
            break
        time.sleep(0.25)
        status, detail = get(f"/api/assets/{asset_id}")
    check(
        "asset detail",
        status == 200 and detail["versions"][0]["processing_status"] == "DONE",
        detail["versions"][0]["processing_status"],
    )

    status, opts = get("/api/assets/filters")
    check(
        "filter options",
        status == 200
        and "IAE-42" in opts["expeditions"]
        and "Maitri" in opts["stations"]
        and bool(opts["asset_types"])
        and bool(opts["access_levels"]),
        opts["expeditions"],
    )

    status, raw = get(f"/api/assets/{asset_id}/versions/{detail['versions'][0]['id']}/download", raw=True)
    check("download original", status == 200 and raw.startswith(b"%PDF-"), f"{len(raw)} bytes")

    status, v2 = multipart(
        f"/api/assets/{asset_id}/versions",
        {"note": "corrected table 2 figure"},
        "IAE42_report.pdf",
        PDF + b"\n% revised revision",
    )
    check(
        "upload second version",
        status == 201
        and v2["version_number"] == 2
        and v2["file_hash"] != detail["versions"][0]["file_hash"],
        f"v{v2.get('version_number')}",
    )

    status, after = get(f"/api/assets/{asset_id}")
    check("versions preserved", len(after["versions"]) == 2, len(after["versions"]))

    status, _ = get("/api/assets/999999")
    check("missing asset 404", status == 404)

    status, bad = multipart(
        "/api/assets", {"meta": "not-json"}, "x.pdf", PDF
    )
    check("invalid metadata 422", status == 422, status)

    status, patched = None, None
    req = urllib.request.Request(
        f"{BASE}/api/assets/{asset_id}",
        data=json.dumps({"title": "42nd IAE Report (revised title)"}).encode(),
        headers={"Content-Type": "application/json"},
        method="PATCH",
    )
    with urllib.request.urlopen(req) as resp:
        patched = json.loads(resp.read())
        status = resp.status
    check("metadata edit", status == 200 and patched["title"].endswith("(revised title)"), status)

    print()
    print(f"{sum(checks)}/{len(checks)} checks passed")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
