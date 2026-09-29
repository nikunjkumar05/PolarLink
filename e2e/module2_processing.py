"""Module 2 e2e: upload -> async processing -> evidence passages -> reprocess."""

import io
import json
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE = "http://localhost:5173"


# ---------------------------------------------------------------- PDF builder
def make_pdf(pages):
    """Build a minimal but valid multi-page PDF with Helvetica text."""

    def esc(text):
        return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")

    font_id = 3 + 2 * len(pages)
    page_ids = [3 + 2 * i for i in range(len(pages))]
    content_ids = [4 + 2 * i for i in range(len(pages))]

    objects = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: (
            f"<</Type/Pages/Kids[{' '.join(f'{i} 0 R' for i in page_ids)}]"
            f"/Count {len(pages)}>>"
        ).encode(),
        font_id: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }

    for index, lines in enumerate(pages):
        objects[page_ids[index]] = (
            f"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
            f"/Contents {content_ids[index]} 0 R"
            f"/Resources<</Font<</F1 {font_id} 0 R>>>>>>"
        ).encode()

        ops = ["BT /F1 11 Tf 48 750 Td"]
        for line_index, line in enumerate(lines):
            if line_index:
                ops.append("0 -14 Td")
            ops.append(f"({esc(line)}) Tj")
        ops.append("ET")
        stream = "\n".join(ops).encode()
        objects[content_ids[index]] = (
            f"<</Length {len(stream)}>>\nstream\n".encode() + stream + b"\nendstream"
        )

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = {}
    for number in sorted(objects):
        offsets[number] = out.tell()
        out.write(f"{number} 0 obj\n".encode() + objects[number] + b"\nendobj\n")

    xref_at = out.tell()
    count = max(objects) + 1
    out.write(f"xref\n0 {count}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for number in range(1, count):
        out.write(f"{offsets[number]:010d} 00000 n \n".encode())
    out.write(
        f"trailer\n<</Size {count}/Root 1 0 R>>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    )
    return out.getvalue()


def long_report_page():
    topics = [
        "Sea ice extent was measured along the coastal transect each morning.",
        "Automatic weather station data was reconciled with manual readings.",
        "Sediment cores were recovered from the meltwater outlet channel.",
        "Benthic samples were preserved and catalogued for shore analysis.",
        "Satellite overpass timings were logged against ground truth points.",
    ]
    lines = []
    for block in range(14):
        lines.append(f"Section {block + 1}. {topics[block % len(topics)]}")
        lines.append(
            "  " + "Recorded values were validated before being committed to the field log. " * 2
        )
    return lines


# ------------------------------------------------------------------- requests
def request(method, path, body=None, headers=None):
    req = urllib.request.Request(BASE + path, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            if "json" in resp.headers.get("Content-Type", ""):
                return resp.status, json.loads(data)
            return resp.status, data
    except urllib.error.HTTPError as exc:
        data = exc.read()
        try:
            data = json.loads(data)
        except Exception:
            pass
        return exc.code, data


def upload(path, filename, content, meta=None, content_type="application/octet-stream"):
    boundary = uuid.uuid4().hex
    body = b""
    if meta is not None:
        body += (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"meta\"\r\n\r\n"
            f"{meta}\r\n"
        ).encode()
    body += (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
        f"filename=\"{filename}\"\r\nContent-Type: {content_type}\r\n\r\n"
    ).encode()
    body += content + f"\r\n--{boundary}--\r\n".encode()
    return request(
        "POST",
        path,
        body,
        {"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )


def wait_terminal(asset_id, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        status, asset = request("GET", f"/api/assets/{asset_id}")
        if status != 200:
            return None, asset
        if all(
            version["processing_status"] in ("DONE", "FAILED")
            for version in asset["versions"]
        ):
            return asset, asset["versions"][-1]
        time.sleep(0.25)
    return None, None


# ---------------------------------------------------------------------- checks
results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}{('  ' + str(extra)) if extra else ''}")


def main():
    pdf = make_pdf([long_report_page(), ["Page two heading.", "Closing statement."]])
    meta = json.dumps(
        {
            "title": "Sea Ice Field Report 2025",
            "asset_type": "PDF",
            "topic": "Sea Ice",
            "expedition": "IAE-42",
            "station": "Maitri",
            "year": 2025,
            "access_level": "PUBLIC",
        }
    )

    status, asset = upload("/api/assets", "sea_ice_report.pdf", pdf, meta, "application/pdf")
    check("upload returns 201", status == 201, status)
    if status != 201:
        return 1
    asset_id = asset["id"]

    asset, version = wait_terminal(asset_id)
    check("processing finished", asset is not None and version is not None)
    if not asset:
        return 1

    check("status DONE", version["processing_status"] == "DONE", version["processing_status"])
    check("page_count == 2", version["page_count"] == 2, version["page_count"])
    check("passage_count > 1", version["passage_count"] > 1, version["passage_count"])
    vid = version["id"]

    status, listing = request("GET", f"/api/versions/{vid}/passages")
    check("list passages 200", status == 200, status)
    check(
        "listing total matches count",
        listing["total"] == version["passage_count"],
        f"{listing['total']} vs {version['passage_count']}",
    )
    check("version summary present", listing["version"]["version_number"] == 1)
    items = listing["items"]
    check(
        "all passages have content + offsets",
        all(i["content"].strip() and i["start_offset"] is not None for i in items),
    )
    check(
        "location_type is PAGE",
        all(i["location_type"] == "PAGE" for i in items),
    )
    check(
        "page numbers in range",
        all(i["page_number"] in (1, 2) for i in items),
        sorted({i["page_number"] for i in items}),
    )
    check(
        "sequence numbers ordered",
        [i["sequence_number"] for i in items] == sorted(i["sequence_number"] for i in items),
    )

    status, pages = request("GET", f"/api/versions/{vid}/pages")
    check("distinct pages endpoint", status == 200 and set(pages) == {1, 2}, pages)

    status, page2 = request("GET", f"/api/versions/{vid}/passages?page_number=2")
    check(
        "filter by page",
        status == 200
        and page2["total"] >= 1
        and all(i["page_number"] == 2 for i in page2["items"]),
        page2["total"],
    )

    status, searched = request("GET", f"/api/versions/{vid}/passages?q=Sediment")
    check("search inside version", status == 200 and searched["total"] >= 1, searched["total"])

    status, one = request("GET", f"/api/versions/{vid}/passages/{items[0]['id']}")
    check("single passage", status == 200 and one["id"] == items[0]["id"])
    status, missing = request("GET", f"/api/versions/{vid}/passages/999999")
    check("missing passage 404", status == 404, status)

    # --- reprocess replaces passages but keeps the original bytes ------------
    status, before_file = request("GET", f"/api/assets/{asset_id}/versions/{vid}/download")
    check("download original works", status == 200 and isinstance(before_file, bytes))
    status, rep = request("POST", f"/api/versions/{vid}/reprocess")
    check("reprocess accepted", status == 200, status)
    asset, version = wait_terminal(asset_id)
    check(
        "reprocess produced passages again",
        version["passage_count"] == listing["total"],
        version["passage_count"],
    )
    status, after_file = request("GET", f"/api/assets/{asset_id}/versions/{vid}/download")
    check("original unchanged after reprocess", before_file == after_file)

    # --- plain text source ---------------------------------------------------
    txt = "Arctic fox population notes.\n\n" + "Transect counts were recorded at dawn. " * 40
    status, text_asset = upload(
        "/api/assets",
        "population_notes.txt",
        txt.encode(),
        json.dumps({"title": "Population Notes", "asset_type": "OTHER"}),
        "text/plain",
    )
    check("txt upload", status == 201, status)
    text_asset, text_version = wait_terminal(text_asset["id"])
    check(
        "txt extracted as TEXT location",
        text_version["processing_status"] == "DONE"
        and text_version["passage_count"] >= 1,
        text_version["passage_count"],
    )
    status, text_listing = request(
        "GET", f"/api/versions/{text_version['id']}/passages"
    )
    check(
        "txt passages have no page",
        all(i["page_number"] is None for i in text_listing["items"]),
    )

    # --- unsupported type degrades gracefully --------------------------------
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    status, png_asset = upload(
        "/api/assets",
        "station_photo.png",
        png,
        json.dumps({"title": "Station Photo", "asset_type": "IMAGE"}),
        "image/png",
    )
    check("image upload", status == 201, status)
    png_asset, png_version = wait_terminal(png_asset["id"])
    check(
        "image processing DONE with warning",
        png_version["processing_status"] == "DONE"
        and png_version["passage_count"] == 0
        and bool(png_version["processing_note"]),
        f"{png_version['processing_status']} / {png_version['processing_note']}",
    )
    check("image original preserved", request(
        "GET", f"/api/assets/{png_asset['id']}/versions/{png_version['id']}/download"
    )[0] == 200)

    # --- asset detail exposes passage counts ---------------------------------
    status, detail = request("GET", f"/api/assets/{asset_id}")
    check(
        "asset detail carries passage_count",
        status == 200 and detail["versions"][0]["passage_count"] > 0,
        detail["versions"][0]["passage_count"],
    )

    print()
    print(f"{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
