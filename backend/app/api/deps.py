from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..services.auth import TokenError, decode_token

_UNSETTLED = object()


def _bearer(request: Request) -> str | None:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip() or None
    return None


def current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """FR-01 — resolve the caller from the bearer token, or 401."""
    token = _bearer(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="sign in required")
    try:
        payload = decode_token(token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    user = db.get(User, int(payload.get("sub", 0)))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="account is inactive")
    return user


def optional_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    """Read-only endpoints work signed out; writes never use this."""
    try:
        return current_user(request, db)
    except HTTPException:
        return None


CurrentUser = Annotated[User, Depends(current_user)]
OptionalUser = Annotated["User | None", Depends(optional_user)]
DbSession = Annotated[Session, Depends(get_db)]


def require_role(user: CurrentUser, *roles: str) -> User:
    """FR-02 — ADMIN always passes; otherwise the role must be listed."""
    if user.role == "ADMIN" or user.role in roles:
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"this action needs the {' or '.join(roles)} role",
    )


__all__ = ["CurrentUser", "DbSession", "OptionalUser", "current_user", "optional_user", "require_role"]