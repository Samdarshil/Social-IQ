"""Builds the unified dataset ("Workspace") that analytics, ML and the assistant all consume.

Demo users get synthetic data (labelled). Real users get only what their connected platforms
returned and was stored. The two are never mixed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache

import pandas as pd
from sqlalchemy.orm import Session

from app.models.tables import ContentRow, User
from app.schemas.content import PLATFORMS, DataSource
from app.services.demo_data import generate_demo
from app.utils.categorize import title_features

COLUMNS = ["platform", "content_id", "content_type", "title", "published_at", "views", "likes", "comments",
           "shares", "followers_gained", "duration_sec", "category"]


@dataclass
class Workspace:
    content: pd.DataFrame
    followers: pd.DataFrame            # date, platform, followers (may be empty for live users)
    accounts: dict                     # platform -> {account_label, followers}
    source: DataSource
    key: str                           # cache key for ML models
    creator_name: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def platforms(self) -> list[str]:
        return [p for p in PLATFORMS if p in set(self.content["platform"])] if len(self.content) else []


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if df.empty:
        df = pd.DataFrame({c: pd.Series(dtype="object") for c in COLUMNS})
        df["published_at"] = pd.to_datetime(df["published_at"], utc=True)
        for c in ("views", "likes", "comments", "shares", "interactions", "hour", "dow", "title_len", "title_words",
                  "has_question", "has_number", "has_emoji", "hashtags", "is_caps_heavy"):
            df[c] = pd.Series(dtype="int64")
        df["engagement_rate"] = pd.Series(dtype="float64")
        df["date"] = df["published_at"].dt.floor("D")
        return df
    df["published_at"] = pd.to_datetime(df["published_at"], utc=True)
    df["interactions"] = df["likes"] + df["comments"] + df["shares"]
    df["engagement_rate"] = (df["interactions"] / df["views"].clip(lower=1)).astype(float)
    df["hour"] = df["published_at"].dt.hour
    df["dow"] = df["published_at"].dt.dayofweek
    df["date"] = df["published_at"].dt.floor("D")
    df["title"] = df["title"].fillna("")
    for k in ("title_len", "title_words", "has_question", "has_number", "has_emoji", "hashtags", "is_caps_heavy"):
        df[k] = [title_features(t)[k] for t in df["title"]]
    return df.sort_values("published_at").reset_index(drop=True)


@lru_cache(maxsize=4)
def _demo_for_day(day: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    content, followers, accounts = generate_demo(datetime.fromisoformat(day).replace(tzinfo=timezone.utc))
    return prepare(content), followers, accounts


def demo_workspace() -> Workspace:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00")
    content, followers, accounts = _demo_for_day(day)
    return Workspace(
        content=content, followers=followers, accounts=accounts, creator_name="Nova Chen (demo)",
        source=DataSource(mode="demo", label="DEMO DATA: synthetic creator, not a real account",
                          platforms_demo=list(accounts)), key=f"demo:{day}")


def user_workspace(user: User, db: Session) -> Workspace:
    if user.is_demo:
        return demo_workspace()
    rows = db.query(ContentRow).filter(ContentRow.user_id == user.id).all()
    df = pd.DataFrame([{c: getattr(r, c) for c in COLUMNS} for r in rows]) if rows else pd.DataFrame(columns=COLUMNS)
    df = prepare(df)
    accounts = {c.platform: {"account_label": c.account_label, "followers": c.followers} for c in user.connections}
    live = sorted(accounts)
    notes = []
    if len(df) and df["platform"].nunique() < len(live):
        notes.append("Some connected platforms returned no content yet.")
    source = DataSource(mode="live" if live else "empty",
                        label="Live data from your connected accounts" if live else "No accounts connected yet",
                        platforms_live=live)
    latest = df["published_at"].max().isoformat() if len(df) else "none"
    return Workspace(content=df, followers=pd.DataFrame(columns=["date", "platform", "followers"]), accounts=accounts,
                     source=source, key=f"user:{user.id}:{len(df)}:{latest}", creator_name=user.display_name, notes=notes)
