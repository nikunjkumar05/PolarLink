from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import alerts, articles, assets, auth, claims, evidence, search
from .config import API_PREFIX, ensure_directories
from .db import init_db

ensure_directories()
init_db()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="PolarLink API",
    description=(
        "Evidence-linked polar knowledge and outreach platform — "
        "Module 1: Repository & Upload, Module 2: Document Processing, "
        "Module 3: Search, Module 4: Claims, Review & Publication, "
        "Module 5: Source-change impact"
    ),
    version="0.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assets.router, prefix=API_PREFIX)
app.include_router(evidence.router, prefix=API_PREFIX)
app.include_router(search.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(claims.router, prefix=API_PREFIX)
app.include_router(articles.router, prefix=API_PREFIX)
app.include_router(alerts.router, prefix=API_PREFIX)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "modules": (
            "repository-upload,document-processing,search,"
            "claims-articles,review-publication,source-impact"
        ),
    }
