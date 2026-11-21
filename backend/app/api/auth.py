from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import rate_limit
from app.db import get_db
from app.models.tables import User
from app.schemas.api import LoginIn, RegisterIn
from app.security.auth import create_access_token, current_user
from app.security.crypto import hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
DEMO_EMAIL = "demo@socialiq.local"


def _user_out(u: User) -> dict:
    return dict(id=u.id, email=u.email if not u.is_demo else None, display_name=u.display_name, is_demo=u.is_demo)


@router.post("/register", dependencies=[Depends(rate_limit(10, 60))])
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email.lower()).first():
        raise HTTPException(409, "An account with this email already exists.")
    u = User(email=body.email.lower(), display_name=body.display_name or body.email.split("@")[0], password_hash=hash_password(body.password))
    db.add(u); db.commit()
    return dict(token=create_access_token(u), user=_user_out(u))


@router.post("/login", dependencies=[Depends(rate_limit(10, 60))])
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == body.email.lower()).first()
    if not u or u.is_demo or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Incorrect email or password.")
    return dict(token=create_access_token(u), user=_user_out(u))


@router.post("/demo", dependencies=[Depends(rate_limit(30, 60))])
def demo(db: Session = Depends(get_db)):
    """Explicit demo session. It serves synthetic data only and can never connect or store real accounts."""
    u = db.query(User).filter(User.email == DEMO_EMAIL).first()
    if not u:
        u = User(email=DEMO_EMAIL, display_name="Nova Chen (demo)", password_hash=hash_password(secrets.token_urlsafe(32)), is_demo=True)
        db.add(u); db.commit()
    return dict(token=create_access_token(u, demo=True), user=_user_out(u))


@router.get("/me")
def me(user: User = Depends(current_user)):
    return _user_out(user)
