"""Prepare a clean, camera-ready PolarLink demo state.

    python scripts/demo.py             # top up, warm the index, write the sample PDF
    python scripts/demo.py --reset     # wipe the repository first, then seed

Does three things that matter while recording:

1. seeds the corpus through the real API so extraction and indexing run exactly
   as they would for a user upload,
2. runs one hybrid search so the embedding model is loaded and the first query
   on camera does not wait for a cold start,
3. writes demo/sample-upload.pdf - a fresh document that is not in the corpus,
   for the upload half of the walkthrough.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

import seed  # noqa: E402  - sibling script, reuses its corpus and PDF writer

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PATH = ROOT / "demo" / "sample-upload.pdf"
SAMPLE_V2_PATH = ROOT / "demo" / "sample-upload-v2.pdf"

SAMPLE_UPLOAD: dict = {
    "filename": "maitri-aws-maintenance-log-2026.pdf",
    "meta": {
        "title": "Maitri Station AWS Maintenance Log 2026",
        "description": "Routine maintenance record for the automatic weather station mast at Maitri.",
        "asset_type": "PDF",
        "topic": "Meteorology",
        "expedition": "41st Indian Antarctic Expedition",
        "station": "Maitri",
        "year": 2026,
        "author": "NCPOR Operations",
        "keywords": "automatic weather station, anemometer, mast, maintenance",
        "attribution": "NCPOR",
        "access_level": "PUBLIC",
    },
    "body": seed.doc(
        "The automatic weather station mast at Maitri was inspected on 14 January 2026. Ice loading on the "
        "cross arms had increased since the previous visit, so every fastener was checked and the de-icing "
        "sleeve around the anemometer was replaced.",
        "The anemometer was recalibrated against the reference cup anemometer carried by the field team. Readings "
        "agreed within four per cent across the full range, and the calibration sheet is filed with this log. The "
        "wind vane bearing was cleaned and re-greased because the tail had started to stick in rime conditions.",
        "Power came from the solar array with the battery bank holding charge overnight. One panel had a thin "
        "coating of settled snow, which was brushed off; no other fault was found on the mast during this visit.",
        "Follow-up: the de-icing sleeve should be inspected again before the next winter season, since the same "
        "component had to be replaced twice in the previous two years.",
    ),
}

# The revised edition. Paragraphs 1 and 2 are deliberately rewritten and a new one
# is appended, so a claim made against v1 is detected as a changed passage when
# this file is uploaded as version 2 (FR-31 → FR-42).
SAMPLE_UPLOAD_V2: dict = {
    **SAMPLE_UPLOAD,
    "filename": "maitri-aws-maintenance-log-2026-revised.pdf",
    "body": seed.doc(
        "The automatic weather station mast at Maitri was inspected on 14 January 2026. Ice loading on the "
        "cross arms had increased since the previous visit, so every fastener was checked and the de-icing "
        "sleeve around the anemometer was replaced. A second visit was made on 3 February 2026 after a wind "
        "event shook the mast.",
        "The anemometer was recalibrated against the reference cup anemometer carried by the field team. Readings "
        "agreed within ELEVEN per cent across the full range, well outside the four per cent tolerance agreed at "
        "calibration, so the instrument was flagged for replacement rather than accepted.",
        "Power came from the solar array with the battery bank holding charge overnight. One panel had a thin "
        "coating of settled snow, which was brushed off; no other fault was found on the mast during this visit.",
        "Follow-up: the de-icing sleeve should be inspected again before the next winter season, since the same "
        "component had to be replaced twice in the previous two years.",
    ),
}


def ensure_users(base: str) -> list[dict]:
    """FR-01 — create the demo accounts if the database has none yet."""
    from seed import ensure_users as seed_users

    return seed_users(base)





def clear_editorial(base: str) -> int:
    """Remove demo claims and articles so a recording starts from an empty desk.

    Assets are deleted by the caller; articles and claims are not tied to an
    asset, so --reset has to clear them explicitly.
    """
    from seed import clear_editorial as seed_clear

    return seed_clear(base)


def wait_for(base: str, asset_id: int, timeout: float = 60.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        detail = requests.get(f"{base}/api/assets/{asset_id}", timeout=30).json()
        statuses = {version["processing_status"] for version in detail["versions"]}
        if statuses <= {"DONE", "FAILED"}:
            return detail
        time.sleep(0.4)
    raise TimeoutError(f"asset {asset_id} did not reach a terminal state")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=seed.DEFAULT_BASE)
    parser.add_argument("--reset", action="store_true", help="delete existing assets first")
    args = parser.parse_args()

    try:
        requests.get(f"{args.base}/api/health", timeout=10).raise_for_status()
    except Exception as exc:  # noqa: BLE001
        print(f"API unreachable at {args.base}: {exc}", file=sys.stderr)
        return 1

    if args.reset:
        removed = clear_editorial(args.base)
        listing = requests.get(f"{args.base}/api/assets?page_size=100", timeout=30).json()
        for item in listing["items"]:
            requests.delete(f"{args.base}/api/assets/{item['id']}", timeout=30)
        print(f"cleared {listing['total']} asset(s) and {removed} claim/article record(s)")

    users = ensure_users(args.base)
    if users:
        print(f"users {len(users)} demo account(s) ready")

    existing = {
        item["title"]
        for item in requests.get(f"{args.base}/api/assets?page_size=100", timeout=30).json()["items"]
    }

    created = 0
    for document in seed.DOCUMENTS:
        title = document["meta"]["title"]
        if title in existing:
            continue
        asset = seed.upload(args.base, document)
        wait_for(args.base, asset["id"])
        created += 1
        print(f"seed  {title}")

    SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SAMPLE_PATH.write_bytes(seed.make_pdf(SAMPLE_UPLOAD["body"]))
    print(f"sample {SAMPLE_PATH.relative_to(ROOT)}")
    SAMPLE_V2_PATH.write_bytes(seed.make_pdf(SAMPLE_UPLOAD_V2["body"]))
    print(f"sample {SAMPLE_V2_PATH.relative_to(ROOT)}  (the revised edition)")

    started = time.time()
    stats = requests.get(
        f"{args.base}/api/search",
        params={"q": "sea ice", "mode": "hybrid", "limit": 5},
        timeout=90,
    ).json()["index"]
    warm_ms = int((time.time() - started) * 1000)

    listing = requests.get(f"{args.base}/api/assets?page_size=1", timeout=30).json()
    print(
        f"\nready in {warm_ms} ms · {listing['total']} assets · "
        f"{stats['keyword_rows']} keyword rows · "
        f"{stats['embedded_passages']}/{stats['total_passages']} passages embedded · "
        f"{stats['embedding_model'] or 'no model'}"
    )
    print(f"{created} new asset(s) created")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
