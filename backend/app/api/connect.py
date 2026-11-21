from __future__ import annotations

import base64
import hashlib
import secrets
import time
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import rate_limit
from app.config import get_settings
from app.db import get_db
from app.integrations.base import ProviderUnavailable
from app.integrations.registry import ADAPTERS, get_adapter
from app.models.tables import ContentRow, PlatformConnection, User
from app.security.auth import create_state_token, current_user, decode_state_token
from app.security.crypto import encrypt_token
from app.services.sync import sync_connection

router = APIRouter(prefix="/api", tags=["connections"])
_PKCE: dict[str, tuple[str, float]] = {}   # nonce -> (verifier, expiry). In-memory: single-process MVP.


def _redirect_uri(platform: str) -> str:
    return f"{get_settings().backend_url}/api/connect/{platform}/callback"


def _adapter_or_404(platform: str):
    try:
        return get_adapter(platform)
    except KeyError:
        raise HTTPException(404, "Unknown platform.")


@router.get("/platforms")
def platforms(user: User = Depends(current_user)):
    conns = {c.platform: c for c in user.connections}
    out = []
    for p, a in ADAPTERS.items():
        c = conns.get(p)
        status = "demo" if user.is_demo else "connected" if c else "available" if a.is_configured() else "not_configured"
        out.append(dict(**a.describe(), status=status, account_label=(c.account_label if c else None),
                        last_synced_at=(c.last_synced_at if c else None),
                        connected_at=(c.connected_at if c else None)))
    return out


@router.post("/connect/{platform}/start", dependencies=[Depends(rate_limit(20, 60))])
def start(platform: str, user: User = Depends(current_user)):
    a = _adapter_or_404(platform)
    if user.is_demo:
        raise HTTPException(409, "Demo sessions use synthetic data and cannot connect real accounts. Create an account to connect.")
    if not a.is_configured():
        raise HTTPException(503, f"{a.label} is not configured on this server (missing OAuth credentials). Demo mode remains available.")
    nonce, challenge = secrets.token_urlsafe(16), None
    if a.uses_pkce:
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        now = time.time()
        for k in [k for k, (_, exp) in _PKCE.items() if exp < now]:
            _PKCE.pop(k, None)
        _PKCE[nonce] = (verifier, now + 600)
    state = create_state_token(dict(uid=user.id, p=platform, n=nonce))
    try:
        url = a.authorization_url(state, _redirect_uri(platform), challenge)
    except ProviderUnavailable as e:
        raise HTTPException(503, str(e))
    return dict(authorization_url=url, scopes=a.read_only_scopes)


@router.get("/connect/{platform}/callback")
def callback(platform: str, code: str | None = None, state: str | None = None, error: str | None = None, db: Session = Depends(get_db)):
    front = get_settings().frontend_url.rstrip("/") + "/app/privacy"
    def back(**q): return RedirectResponse(f"{front}?{urlencode(q)}")
    if error or not code or not state:
        return back(error=f"{platform} authorization was cancelled or denied")
    st = decode_state_token(state)
    if st.get("p") != platform:
        return back(error="OAuth state mismatch")
    user = db.get(User, int(st["uid"]))
    if not user or user.is_demo:
        return back(error="Unknown user")
    a = get_adapter(platform)
    verifier = (_PKCE.pop(st["n"], (None, 0))[0]) if a.uses_pkce else None
    try:
        tokens = a.exchange_code(code, _redirect_uri(platform), verifier)
        acct = a.fetch_account(tokens)
        conn = db.query(PlatformConnection).filter_by(user_id=user.id, platform=platform).first() or PlatformConnection(user_id=user.id, platform=platform)
        conn.account_label, conn.followers = acct.account_label, acct.followers
        conn.scopes = " ".join(tokens.scopes or a.read_only_scopes)
        conn.access_token_enc = encrypt_token(tokens.access_token)
        conn.refresh_token_enc = encrypt_token(tokens.refresh_token) if tokens.refresh_token else None
        conn.expires_at = tokens.expires_at
        db.add(conn); db.commit()
        n = sync_connection(db, conn)
    except ProviderUnavailable as e:
        # Do not keep a connection that cannot deliver data: that would look "connected" while empty.
        c = db.query(PlatformConnection).filter_by(user_id=user.id, platform=platform).first()
        if c:
            db.delete(c); db.commit()
        return back(error=str(e))
    return back(connected=platform, synced=n)


@router.post("/connections/{platform}/sync", dependencies=[Depends(rate_limit(10, 60))])
def sync(platform: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    conn = db.query(PlatformConnection).filter_by(user_id=user.id, platform=platform).first()
    if not conn:
        raise HTTPException(404, "Platform is not connected.")
    try:
        return dict(synced=sync_connection(db, conn))
    except ProviderUnavailable as e:
        raise HTTPException(502, str(e))


@router.delete("/connections/{platform}")
def disconnect(platform: str, delete_data: bool = True, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.is_demo:
        raise HTTPException(409, "Demo data is synthetic and not stored; nothing to disconnect.")
    conn = db.query(PlatformConnection).filter_by(user_id=user.id, platform=platform).first()
    if not conn:
        raise HTTPException(404, "Platform is not connected.")
    db.delete(conn)   # tokens are removed with the row
    removed = 0
    if delete_data:
        removed = db.query(ContentRow).filter_by(user_id=user.id, platform=platform).delete()
    db.commit()
    return dict(disconnected=platform, content_removed=removed,
                note="Stored tokens were deleted. To fully revoke SocialIQ's access, also remove it in the platform's own security settings.")
