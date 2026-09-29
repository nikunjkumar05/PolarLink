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


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
