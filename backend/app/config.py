from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("POLARLINK_DATA_DIR", BACKEND_DIR / "data"))
STORAGE_DIR = Path(os.environ.get("POLARLINK_STORAGE_DIR", BACKEND_DIR / "storage"))
DB_PATH = DATA_DIR / "polarlink.db"
DATABASE_URL = os.environ.get("POLARLINK_DATABASE_URL", f"sqlite:///{DB_PATH}")

ALLOWED_ASSET_TYPES = ("PDF", "IMAGE", "VIDEO", "DATASET", "ACTIVITY", "OTHER")
ALLOWED_ACCESS_LEVELS = ("PUBLIC", "INTERNAL", "RESTRICTED")
ALLOWED_PROCESSING_STATUSES = ("PENDING", "PROCESSING", "DONE", "FAILED")

MAX_UPLOAD_BYTES = 200 * 1024 * 1024

API_PREFIX = "/api"

# FR-01 — signed sessions for the editorial side of the platform.
JWT_SECRET = os.environ.get("POLARLINK_JWT_SECRET", "polarlink-dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_TTL_SECONDS = int(os.environ.get("POLARLINK_JWT_TTL", str(12 * 60 * 60)))
# Seeded demo credentials; demo.py --reset recreates them. Documented in README.
SEED_USERS = (
    ("admin@ncpor.in", "Dr. Meera Raghavan", "ADMIN", "admin123"),
    ("editor@ncpor.in", "Arjun Nair", "EDITOR", "editor123"),
    ("reviewer@ncpor.in", "Lt. Kavya Iyer", "REVIEWER", "reviewer123"),
)

# FR-18 — optional LLM drafting. When no key is present the extractive
# composer is used instead, so the feature never depends on the network.
LLM_API_KEY = os.environ.get("POLARLINK_LLM_KEY")
LLM_BASE_URL = os.environ.get("POLARLINK_LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.environ.get("POLARLINK_LLM_MODEL", "gpt-4o-mini")
LLM_TIMEOUT = float(os.environ.get("POLARLINK_LLM_TIMEOUT", "45"))


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
