"""SocialIQ's own authentication: JWT bearer tokens. Demo sessions are explicit and flagged."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models.tables import User

_bearer = HTTPBearer(auto_error=False)
ALGO = "HS256"


def create_access_token(user: User, *, demo: bool = False) -> str:
    s = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=s.jwt_ttl_minutes)
    return jwt.encode({"sub": str(user.id), "demo": demo, "exp": exp, "typ": "access"}, s.jwt_secret, ALGO)


def create_state_token(payload: dict, minutes: int = 10) -> str:
    s = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return jwt.encode({**payload, "exp": exp, "typ": "oauth_state"}, s.jwt_secret, ALGO)


def decode_state_token(token: str) -> dict:
    try:
        data = jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGO])
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state") from exc
    if data.get("typ") != "oauth_state":
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    return data


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        data = jwt.decode(creds.credentials, get_settings().jwt_secret, algorithms=[ALGO])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired session") from exc
    if data.get("typ") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user = db.get(User, int(data["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return user
