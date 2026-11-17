"""Persistence models. Only what the product needs: users, platform connections, synced content."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(80), default="")
    password_hash: Mapped[str] = mapped_column(String(100))
    is_demo: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    connections: Mapped[list["PlatformConnection"]] = relationship(
        back_populates="user", cascade="all, delete-orphan")
    content: Mapped[list["ContentRow"]] = relationship(
        back_populates="user", cascade="all, delete-orphan")


class PlatformConnection(Base):
    __tablename__ = "platform_connections"
    __table_args__ = (UniqueConstraint("user_id", "platform"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(20))
    account_label: Mapped[str] = mapped_column(String(120), default="")
    followers: Mapped[int] = mapped_column(Integer, default=0)
    scopes: Mapped[str] = mapped_column(Text, default="")
    access_token_enc: Mapped[str] = mapped_column(Text)           # Fernet-encrypted
    refresh_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)  # Fernet-encrypted
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user: Mapped[User] = relationship(back_populates="connections")


class ContentRow(Base):
    __tablename__ = "content"
    __table_args__ = (UniqueConstraint("user_id", "platform", "content_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(20))
    content_id: Mapped[str] = mapped_column(String(100))
    content_type: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    followers_gained: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category: Mapped[str] = mapped_column(String(40), default="General")
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    user: Mapped[User] = relationship(back_populates="content")
