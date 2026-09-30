from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .claim import ClaimOut


class ArticleClaimOut(BaseModel):
    position: int
    claim: ClaimOut


class ArticleSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    status: str
    summary: str | None = None
    audience: str | None = None
    author_id: int | None = None
    author_name: str | None = None
    generation_mode: str | None = None
    needs_reverification: bool = False
    claim_count: int = 0
    open_alert_count: int = 0
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None


class ArticleOut(ArticleSummary):
    body: str | None = None
    generation_model: str | None = None
    generation_note: str | None = None
    claims: list[ArticleClaimOut] = Field(default_factory=list)
    open_alerts: list[int] = Field(default_factory=list)


class ArticleCreate(BaseModel):
    title: str = Field(min_length=8, max_length=500)
    summary: str | None = Field(default=None, max_length=2000)
    audience: str | None = Field(default=None, max_length=120)
    claim_ids: list[int] = Field(min_length=1)


class ArticleGenerate(BaseModel):
    """Regenerate the body from the article's claims."""

    mode: str = Field(default="auto", pattern="^(auto|extractive|llm)$")


class ArticleList(BaseModel):
    total: int
    items: list[ArticleSummary]


class TransitionRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=1000)


class ReviewEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    comment: str | None = None
    from_status: str | None = None
    to_status: str | None = None
    actor_name: str | None = None
    created_at: datetime


class PublicArticleOut(BaseModel):
    """FR-27 — what a reader sees. No internal ids, no workflow state."""

    title: str
    summary: str | None = None
    body: str
    author_name: str | None = None
    published_at: datetime | None = None
    audience: str | None = None
    claims: list[ClaimOut]