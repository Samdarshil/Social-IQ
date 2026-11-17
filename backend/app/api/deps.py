from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.tables import User
from app.security.auth import current_user
from app.services import analytics as A
from app.services.dataset import Workspace, user_workspace


def workspace(user: User = Depends(current_user), db: Session = Depends(get_db)) -> Workspace:
    return user_workspace(user, db)


def filters(days: int | None = Query(None, ge=1, le=730), platforms: str | None = Query(None, max_length=80),
            category: str | None = Query(None, max_length=40), content_type: str | None = Query(None, max_length=30)) -> A.Filters:
    plats = [p for p in (platforms or "").split(",") if p in ("youtube", "instagram", "x", "linkedin")] or None
    return A.Filters(days=days, platforms=plats, category=category, content_type=content_type)


_hits: dict[str, deque] = defaultdict(deque)


def rate_limit(max_calls: int, per_seconds: int):
    """Small in-memory limiter (per client IP + path). Fine for a single-process MVP; use Redis when scaling out."""
    def dep(request: Request):
        key = f"{request.client.host if request.client else 'x'}:{request.url.path}"
        now, q = time.monotonic(), _hits[key]
        while q and now - q[0] > per_seconds:
            q.popleft()
        if len(q) >= max_calls:
            raise HTTPException(status_code=429, detail="Too many requests. Please wait a moment and try again.")
        q.append(now)
    return dep
