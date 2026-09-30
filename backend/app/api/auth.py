from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..models import User
from ..services.auth import create_token, hash_password, verify_password
from .deps import CurrentUser, DbSession

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=200)


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    name: str = Field(min_length=2, max_length=200)
    role: str = Field(default="EDITOR", pattern="^(ADMIN|EDITOR|REVIEWER)$")
    password: str = Field(min_length=8, max_length=200)


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: DbSession) -> LoginResponse:
    """FR-01 — exchange credentials for a signed session token."""
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="email or password is wrong"
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    token, expires_in = create_token(user.id, user.role, user.email)
    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserOut(id=user.id, email=user.email, name=user.name, role=user.role),
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DbSession) -> User:
    """FR-01 — the first account created becomes ADMIN; later sign-ups choose
    their own role. A real deployment would restrict this to an invite list."""
    email = payload.email.strip().lower()
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email is taken")

    role = "ADMIN" if db.scalar(select(User.id).limit(1)) is None else payload.role
    user = User(
        email=email,
        name=payload.name.strip(),
        role=role,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user


@router.get("/directory", response_model=list[UserOut])
def directory(db: DbSession) -> list[User]:
    """Accounts shown on the sign-in screen so reviewers know what to pick."""
    return list(db.scalars(select(User).order_by(User.id)).all())


__all__ = [
    "LoginRequest",
    "LoginResponse",
    "RegisterRequest",
    "UserOut",
    "router",
]