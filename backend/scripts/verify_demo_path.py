"""Walk the exact demo path a judge would watch, using only the two demo PDFs.

    1. upload demo/sample-upload.pdf
    2. search it, claim the anemometer passage
    3. build, review and publish an article from that claim
    4. upload demo/sample-upload-v2.pdf as a new version of the same asset
    5. confirm the alert fires, then re-verify
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.demo import SAMPLE_UPLOAD, SAMPLE_UPLOAD_V2  # noqa: E402
from scripts.seed import make_pdf, wait_for  # noqa: E402

BASE = "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parents[2]
PASSED, FAILED = [], []


def check(label: str, condition: bool, detail: str = "") -> None:
    (PASSED if condition else FAILED).append(label)
    print(f"{'PASS' if condition else 'FAIL'}  {label}" + (f"  [{detail}]" if detail else ""))


def token(email: str) -> str:
    r = requests.post(
        f"{BASE}/api/auth/login", json={"email": email, "password": f"{email.split('@')[0].split('.')[0]}123"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def auth(t: str) -> dict:
    return {"Authorization": f"Bearer {t}"}


def upload_asset(document: dict) -> dict:
    r = requests.post(
        f"{BASE}/api/assets",
        files={"file": (document["filename"], make_pdf(document["body"]), "application/pdf")},
        data={"meta": __import__("json").dumps(document["meta"])},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def main() -> int:
    editor = token("editor@ncpor.in")
    reviewer = token("reviewer@ncpor.in")

    # ---------------------------------------------------------- beat 2: upload
    asset = upload_asset(SAMPLE_UPLOAD)
    detail = wait_for(BASE, asset["id"])
    v1 = detail["versions"][0]
    check("beat 2 — sample-upload.pdf processes", v1["processing_status"] == "DONE", f"{v1['passage_count']} passages")

    # ---------------------------------------------------------- beat 3/4: search
    hits = requests.get(
        f"{BASE}/api/search", params={"q": "anemometer", "mode": "hybrid", "limit": 5}, timeout=60
    ).json()
    check("beat 3 — the new upload ranks first", hits["items"][0]["asset"]["id"] == asset["id"],
          hits["items"][0]["asset"]["title"][:40])
    hit = hits["items"][0]
    check("beat 4 — hit carries page + evidence id", hit["passage"]["page_number"] is not None,
          f"v{hit['version']['version_number']} p.{hit['passage']['page_number']} E{hit['passage']['id']}")

    # ---------------------------------------------------------- beat 7: claim
    r = requests.post(
        f"{BASE}/api/claims",
        headers=auth(editor),
        json={
            "text": "The anemometer at Maitri was reading within four per cent of the reference after recalibration.",
            "topic": "Meteorology",
            "evidence": [{"passage_id": hit["passage"]["id"], "relation": "SUPPORTS"}],
        },
        timeout=30,
    )
    check("beat 7 — claim created from the passage", r.status_code == 201, str(r.status_code))
    claim = r.json()

    # ---------------------------------------------------------- beat 8: article
    r = requests.post(
        f"{BASE}/api/articles",
        headers=auth(editor),
        json={
            "title": "Keeping the weather station honest at Maitri",
            "summary": "How a routine calibration on the polar plateau caught a drifting instrument.",
            "audience": "general public",
            "claim_ids": [claim["id"]],
        },
        timeout=30,
    )
    check("beat 8 — article generated from the claim", r.status_code == 201, str(r.status_code))
    article = r.json()
    article_id = article["id"]
    check("beat 8 — body composed only from cited text", bool(article["body"]) and article["generation_mode"] == "extractive",
          f"{len(article['body'])} chars")

    # ---------------------------------------------------------- beat 9: workflow
    for target, who, expect in (("IN_REVIEW", editor, 200), ("APPROVED", reviewer, 200), ("PUBLISHED", reviewer, 200)):
        r = requests.post(f"{BASE}/api/articles/{article_id}/transition?target={target}",
                          headers=auth(who), json={}, timeout=30)
        check(f"beat 9 — {target}", r.status_code == expect, str(r.status_code))

    r = requests.get(f"{BASE}/api/articles/by-slug/{article['slug']}", timeout=30)
    check("beat 10 — public page renders", r.status_code == 200 and r.json()["body"], str(r.status_code))

    # ---------------------------------------------------------- beat 11: v2 upload
    r = requests.post(
        f"{BASE}/api/assets/{asset['id']}/versions",
        files={"file": ("maitri-aws-maintenance-log-2026-revised.pdf", make_pdf(SAMPLE_UPLOAD_V2["body"]), "application/pdf")},
        data={"note": "Revised edition — recalibration figures corrected"},
        headers=auth(editor),
        timeout=30,
    )
    check("beat 11 — revised file accepted as v2", r.status_code in (200, 201), str(r.status_code))
    detail = wait_for(BASE, asset["id"])
    check("beat 11 — asset now has 2 immutable versions", len(detail["versions"]) == 2,
          ", ".join(f"v{v['version_number']}={v['processing_status']}" for v in detail["versions"]))

    # ---------------------------------------------------------- beat 12: alert
    alerts = requests.get(f"{BASE}/api/alerts", params={"status": "OPEN", "article_id": article_id}, timeout=30).json()
    check("beat 12 — impact alert raised automatically", alerts["total"] > 0, f"{alerts['total']} open")
    alert = alerts["items"][0]
    check("beat 12 — old quote preserved for comparison", bool(alert["previous_quote"]))
    check("beat 12 — new quote shows the corrected figure", "ELEVEN" in (alert["current_quote"] or "").upper())

    art = requests.get(f"{BASE}/api/articles/{article_id}", timeout=30).json()
    check("beat 12 — article flagged re-verification required", art["needs_reverification"] is True)
    check("beat 12 — claim marked STALE", art["claims"][0]["claim"]["status"] == "STALE")

    candidates = requests.get(f"{BASE}/api/alerts/{alert['id']}/passages", timeout=30).json()
    r = requests.post(
        f"{BASE}/api/alerts/{alert['id']}/resolve",
        headers=auth(reviewer),
        json={
            "status": "REVERIFIED",
            "note": "The four per cent figure was superseded; the claim needs rewriting before republication.",
            "current_passage_id": candidates[0]["id"] if candidates else None,
        },
        timeout=30,
    )
    check("beat 12 — reviewer re-verifies", r.status_code == 200 and r.json()["status"] == "REVERIFIED", str(r.status_code))
    art = requests.get(f"{BASE}/api/articles/{article_id}", timeout=30).json()
    check("beat 12 — claim now VERIFIED", art["claims"][0]["claim"]["status"] == "VERIFIED")

    # ---------------------------------------------------------- teardown
    requests.delete(f"{BASE}/api/assets/{asset['id']}", timeout=30)
    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    if FAILED:
        print("failed: " + ", ".join(FAILED))
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())