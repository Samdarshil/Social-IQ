from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import rate_limit
from app.config import get_settings
from app.db import get_db
from app.integrations.registry import ADAPTERS
from app.models.tables import ContentRow, PlatformConnection, User
from app.security.auth import current_user
from app.services.analytics import clean

router = APIRouter(prefix="/api/privacy", tags=["privacy"])


@router.get("/overview")
def overview(user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = get_settings()
    n_content = db.query(ContentRow).filter_by(user_id=user.id).count()
    conns = [dict(platform=c.platform, account_label=c.account_label, scopes=c.scopes.split(), connected_at=c.connected_at,
                  last_synced_at=c.last_synced_at, access="read-only") for c in user.connections]
    return clean(dict(
        is_demo=user.is_demo, connections=conns, stored_content_rows=n_content,
        permissions={p: dict(label=a.label, scopes=a.read_only_scopes, notes=a.api_notes) for p, a in ADAPTERS.items()},
        stores=["Your SocialIQ email and a bcrypt hash of your SocialIQ password (never your social-media passwords)",
                "OAuth tokens, encrypted at rest with Fernet (AES-128-CBC + HMAC) using a server-side key",
                "Post-level metrics synced from connected platforms: views, likes, comments, shares, title/caption text, timestamps, category"],
        never_stores=["Social-media passwords", "Direct messages", "Private account content beyond post metrics", "Payment details"],
        ai=dict(provider_configured=bool(s.gemini_api_key), provider="Google Gemini" if s.gemini_api_key else None, model=s.gemini_model if s.gemini_api_key else None,
                sends=["Your question", "Aggregated metrics and model results returned by SocialIQ tools", "Truncated post titles when a question needs them"],
                never_sends=["Account handles or names", "Email address", "OAuth tokens or API secrets", "Passwords"],
                note=("Questions are answered by Google Gemini, which receives the data above." if s.gemini_api_key else
                      "No language-model key is configured, so nothing is sent to an AI provider. The built-in router answers using local tools.")),
        security=dict(oauth_only=True, read_only_scopes=True, token_encryption="Fernet (AES-128-CBC + HMAC-SHA256)", password_hashing="bcrypt",
                      transport="HTTPS must be provided by the deployment (not enforced in local development)",
                      not_claimed=["No SOC 2 / ISO certification", "No third-party penetration test", "Single-process in-memory rate limiting only"])))


@router.get("/export", dependencies=[Depends(rate_limit(5, 60))])
def export(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.is_demo:
        raise HTTPException(409, "Demo data is synthetic and is not stored for export.")
    rows = db.query(ContentRow).filter_by(user_id=user.id).all()
    return clean(dict(
        account=dict(email=user.email, display_name=user.display_name, created_at=user.created_at),
        connections=[dict(platform=c.platform, account_label=c.account_label, followers=c.followers, scopes=c.scopes, connected_at=c.connected_at,
                          last_synced_at=c.last_synced_at) for c in user.connections],   # tokens are deliberately excluded
        content=[dict(platform=r.platform, content_id=r.content_id, content_type=r.content_type, title=r.title, published_at=r.published_at,
                      views=r.views, likes=r.likes, comments=r.comments, shares=r.shares, category=r.category) for r in rows]))


@router.delete("/data")
def delete_data(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Removes all synced analytics and disconnects every platform. The SocialIQ account itself is kept."""
    if user.is_demo:
        raise HTTPException(409, "Demo data is synthetic and is not stored; nothing to delete.")
    n = db.query(ContentRow).filter_by(user_id=user.id).delete()
    c = db.query(PlatformConnection).filter_by(user_id=user.id).delete()
    db.commit()
    return dict(content_deleted=n, connections_deleted=c)


@router.delete("/account")
def delete_account(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.is_demo:
        raise HTTPException(409, "The demo account cannot be deleted.")
    db.delete(user); db.commit()
    return dict(deleted=True)
