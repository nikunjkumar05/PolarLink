"""End-to-end smoke test of the claim -> article -> review -> publish -> impact loop."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import SEED_USERS  # noqa: E402
from scripts.seed import DOCUMENTS, ensure_users, make_pdf, upload, wait_for  # noqa: E402

BASE = "http://127.0.0.1:8000"
FRONT = "http://localhost:5173"
PASSED, FAILED = [], []


def check(label: str, condition: bool, detail: str = "") -> None:
    (PASSED if condition else FAILED).append(label)
    print(f"{'PASS' if condition else 'FAIL'}  {label}" + (f"  [{detail}]" if detail else ""))


def token(email: str, password: str) -> str:
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def auth(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}"}


def main() -> int:
    ensure_users(BASE)

    # ---------------------------------------------------------------- auth
    r = requests.get(f"{BASE}/api/auth/directory", timeout=30)
    check("user directory lists seeded accounts", len(r.json()) >= 3, f"{len(r.json())} users")

    r = requests.post(f"{BASE}/api/auth/login", json={"email": "editor@ncpor.in", "password": "wrongpass"}, timeout=30)
    check("bad password is rejected", r.status_code == 401, str(r.status_code))

    r = requests.get(f"{BASE}/api/claims", timeout=30)
    check("claims endpoint needs no token", r.status_code == 200, str(r.status_code))

    editor = token("editor@ncpor.in", "editor123")
    reviewer = token("reviewer@ncpor.in", "reviewer123")
    check("editor and reviewer can sign in", bool(editor and reviewer))

    r = requests.get(f"{BASE}/api/claims", headers=auth(editor), timeout=30)
    check("token is accepted", r.status_code == 200)

    # ---------------------------------------------------------------- evidence
    s = requests.get(f"{BASE}/api/search", params={"q": "fox kits", "mode": "hybrid", "limit": 5}, timeout=60).json()
    check("seeded corpus is searchable", s["total"] > 0, f"{s['total']} hits")
    hit = s["items"][0]
    passage_id = hit["passage"]["id"]
    asset_id = hit["asset"]["id"]
    version_id = hit["version"]["id"]

    # ---------------------------------------------------------------- claims
    r = requests.post(
        f"{BASE}/api/claims",
        headers=auth(editor),
        json={
            "text": "Arctic fox kits were born at Ny-Alesund in the 2024 survey season.",
            "topic": "Wildlife",
            "evidence": [{"passage_id": passage_id, "relation": "SUPPORTS"}],
        },
        timeout=30,
    )
    check("claim created with evidence", r.status_code == 201, f"{r.status_code} {r.text[:120]}")
    claim = r.json()
    check("claim is SUPPORTED and cites 1 passage", claim["status"] == "SUPPORTED" and len(claim["evidence_links"]) == 1)
    check("claim evidence carries page + version", claim["evidence_links"][0]["evidence"]["page_number"] is not None
          and claim["evidence_links"][0]["evidence"]["version_number"] == 1)

    r = requests.post(
        f"{BASE}/api/claims",
        headers=auth(editor),
        json={"text": "A claim with no evidence at all must not be accepted."},
        timeout=30,
    )
    check("claim without evidence is refused (FR-20)", r.status_code == 422, str(r.status_code))

    r = requests.post(f"{BASE}/api/claims", headers=auth(editor), json={
        "text": "This is a valid length claim but the passage id is bogus.",
        "evidence": [{"passage_id": 999999}],
    }, timeout=30)
    check("claim with unknown passage is refused", r.status_code == 404, str(r.status_code))

    # ---------------------------------------------------------------- article
    r = requests.get(f"{BASE}/api/capabilities", timeout=30).json()
    mode = r["default_mode"]
    print(f"      drafting mode: {mode}")

    r = requests.post(
        f"{BASE}/api/articles",
        headers=auth(editor),
        json={
            "title": "Arctic Fox Breeding Season at Ny-Alesund, 2024",
            "summary": "What the 2024 survey found about fox reproduction at the station.",
            "audience": "general public",
            "claim_ids": [claim["id"]],
        },
        timeout=30,
    )
    check("article created from claim", r.status_code == 201, f"{r.status_code} {r.text[:160]}")
    article = r.json()
    article_id = article["id"]
    check("article body was generated", bool(article["body"]) and len(article["body"]) > 80,
          f"{article['generation_mode']} len={len(article['body'] or '')}")
    check("article starts as DRAFT", article["status"] == "DRAFT")
    check("article holds the claim", len(article["claims"]) == 1)

    # ---------------------------------------------------------------- workflow
    r = requests.post(f"{BASE}/api/articles/{article_id}/transition?target=APPROVED",
                      headers=auth(editor), json={}, timeout=30)
    check("editor cannot approve (FR-02)", r.status_code == 403, str(r.status_code))

    r = requests.post(f"{BASE}/api/articles/{article_id}/transition?target=PUBLISHED",
                      headers=auth(reviewer), json={}, timeout=30)
    check("cannot publish straight from DRAFT (BR-07)", r.status_code == 409, str(r.status_code))

    r = requests.post(f"{BASE}/api/articles/{article_id}/transition?target=IN_REVIEW",
                      headers=auth(editor), json={"comment": "Ready for a reviewer."}, timeout=30)
    check("editor submits for review", r.status_code == 200 and r.json()["status"] == "IN_REVIEW", str(r.status_code))

    r = requests.post(f"{BASE}/api/articles/{article_id}/transition?target=APPROVED",
                      headers=auth(reviewer), json={"comment": "Checked against the source."}, timeout=30)
    check("reviewer approves", r.status_code == 200 and r.json()["status"] == "APPROVED", str(r.status_code))

    r = requests.post(f"{BASE}/api/articles/{article_id}/transition?target=PUBLISHED",
                      headers=auth(reviewer), json={}, timeout=30)
    check("reviewer publishes", r.status_code == 200 and r.json()["status"] == "PUBLISHED", str(r.status_code))
    slug = r.json()["slug"]

    r = requests.get(f"{BASE}/api/articles/by-slug/{slug}", timeout=30)
    check("published article has a public URL", r.status_code == 200 and r.json()["title"].startswith("Arctic Fox"), str(r.status_code))

    r = requests.get(f"{BASE}/api/articles/by-slug/does-not-exist", timeout=30)
    check("unknown slug is 404", r.status_code == 404)

    events = requests.get(f"{BASE}/api/articles/{article_id}/events", timeout=30).json()
    actions = [e["action"] for e in events]
    check("audit trail records every transition",
          "ARTICLE_DRAFTED" in actions and "ARTICLE_IN_REVIEW" in actions
          and "ARTICLE_APPROVED" in actions and "ARTICLE_PUBLISHED" in actions, ", ".join(actions))
    check("audit trail names the actor", any(e["actor_name"] for e in events))

    # ---------------------------------------------------------------- impact
    source = next(d for d in DOCUMENTS if d["meta"]["title"] == hit["asset"]["title"])
    # Unique per run, so re-running the script against a dirty database still
    # produces a genuinely different file hash.
    marker = f"REVISED EDITION {int(time.time())}: the survey team recorded a smaller litter than first reported."
    changed = dict(source)
    changed["body"] = [list(page) + [marker] for page in source["body"]]
    before = requests.get(f"{BASE}/api/assets/{asset_id}", timeout=30).json()
    versions_before = len(before["versions"])
    meta = requests.post(f"{BASE}/api/assets/{asset_id}/versions",
                         files={"file": ("arctic-fox-2024-revised.pdf", make_pdf(changed["body"]), "application/pdf")},
                         data={"note": "Revised edition"}, headers=auth(editor), timeout=30)
    check("changed version uploaded", meta.status_code in (200, 201), str(meta.status_code))
    wait_for(BASE, asset_id)

    detail = requests.get(f"{BASE}/api/assets/{asset_id}", timeout=30).json()
    check("asset gained a new immutable version", len(detail["versions"]) == versions_before + 1,
          f"{versions_before} -> {len(detail['versions'])}")
    newest = max(detail["versions"], key=lambda v: v["version_number"])
    older = sorted(detail["versions"], key=lambda v: v["version_number"])[-2]
    check("the new version is a genuinely different file", newest["file_hash"] != older["file_hash"])

    alerts = requests.get(f"{BASE}/api/alerts", params={"status": "OPEN", "article_id": article_id},
                          timeout=30).json()
    check("source change raised impact alerts for this article", alerts["total"] > 0, f"{alerts['total']} open")
    alert = alerts["items"][0] if alerts["items"] else None
    check("alert names the affected article", alert is not None and alert["article_id"] == article_id)
    check("alert quotes the old evidence", bool(alert and alert["previous_quote"]))
    check("alert shows the new passage and page", bool(alert and alert["current_page_number"]))
    check("alert points at the new version", bool(alert and alert["current_version_id"] == newest["id"]))

    art = requests.get(f"{BASE}/api/articles/{article_id}", timeout=30).json()
    check("published article is flagged for re-verification", art["needs_reverification"] is True)
    check("affected claim went STALE", art["claims"][0]["claim"]["status"] == "STALE")

    # ---------------------------------------------------------------- reverify
    r = requests.post(f"{BASE}/api/alerts/{alert['id']}/resolve", headers=auth(editor),
                      json={"status": "ACKNOWLEDGED"}, timeout=30)
    check("editor cannot resolve an alert", r.status_code == 403, str(r.status_code))

    new_passage = alert["current_passage_id"]
    r = requests.post(f"{BASE}/api/alerts/{alert['id']}/resolve", headers=auth(reviewer),
                      json={"status": "REVERIFIED", "note": "Claim still holds after the edit.",
                            "current_passage_id": new_passage}, timeout=30)
    check("reviewer re-verifies the claim", r.status_code == 200 and r.json()["status"] == "REVERIFIED", str(r.status_code))

    art = requests.get(f"{BASE}/api/articles/{article_id}", timeout=30).json()
    check("claim is now VERIFIED", art["claims"][0]["claim"]["status"] == "VERIFIED")
    check("article flag cleared once alerts are closed", art["needs_reverification"] is False)

    r = requests.get(f"{BASE}/api/alerts/{alert['id']}/passages", timeout=30).json()
    check("reviewer can pick a replacement passage", len(r) > 0, f"{len(r)} candidates")

    # ---------------------------------------------------------------- teardown
    r = requests.delete(f"{BASE}/api/articles/{article_id}", headers=auth(editor), timeout=30)
    check("article can be deleted", r.status_code == 204, str(r.status_code))

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    if FAILED:
        print("failed: " + ", ".join(FAILED))
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())