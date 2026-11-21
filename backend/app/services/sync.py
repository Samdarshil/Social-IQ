"""Pulls content from a connected platform into the unified store. Real data only: nothing is invented on failure."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.integrations.base import ProviderUnavailable, TokenSet
from app.integrations.registry import get_adapter
from app.models.tables import ContentRow, PlatformConnection
from app.security.crypto import decrypt_token, encrypt_token


def tokens_of(conn: PlatformConnection) -> TokenSet:
    return TokenSet(decrypt_token(conn.access_token_enc), decrypt_token(conn.refresh_token_enc) if conn.refresh_token_enc else None,
                    conn.expires_at, conn.scopes.split() if conn.scopes else None)


def sync_connection(db: Session, conn: PlatformConnection) -> int:
    adapter = get_adapter(conn.platform)
    tokens = tokens_of(conn)
    if conn.expires_at and conn.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        tokens = adapter.refresh(tokens)  # raises ProviderUnavailable if not possible
        conn.access_token_enc = encrypt_token(tokens.access_token)
        conn.expires_at = tokens.expires_at
    items = adapter.fetch_content(tokens)
    acct = adapter.fetch_account(tokens)
    conn.followers, conn.account_label = acct.followers, acct.account_label
    existing = {r.content_id: r for r in db.query(ContentRow).filter(ContentRow.user_id == conn.user_id, ContentRow.platform == conn.platform)}
    for c in items:
        row = existing.get(c.content_id) or ContentRow(user_id=conn.user_id, platform=c.platform, content_id=c.content_id)
        for k in ("content_type", "title", "published_at", "views", "likes", "comments", "shares", "followers_gained", "duration_sec", "category"):
            setattr(row, k, getattr(c, k))
        row.meta = c.metadata
        db.add(row)
    conn.last_synced_at = datetime.now(timezone.utc)
    db.commit()
    return len(items)


__all__ = ["sync_connection", "tokens_of", "ProviderUnavailable"]
