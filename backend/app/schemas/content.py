"""Unified internal social-media schema. Analytics and ML only ever see these shapes."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Platform = Literal["youtube", "instagram", "x", "linkedin"]
PLATFORMS: list[str] = ["youtube", "instagram", "x", "linkedin"]
PLATFORM_LABELS = {"youtube": "YouTube", "instagram": "Instagram", "x": "X", "linkedin": "LinkedIn"}
CATEGORIES = ["Tutorials", "Behind the Scenes", "Opinions", "Case Studies", "News & Trends", "Q&A"]
CONTENT_TYPES = {
    "youtube": ["video", "short"],
    "instagram": ["reel", "carousel", "image"],
    "x": ["post", "thread"],
    "linkedin": ["post", "article", "carousel"],
}


class Content(BaseModel):
    platform: Platform
    content_id: str
    content_type: str
    title: str
    published_at: datetime
    views: int = Field(ge=0)            # views / impressions
    likes: int = Field(ge=0)
    comments: int = Field(ge=0)
    shares: int = Field(ge=0)           # shares / reposts / saves-as-share
    followers_gained: int | None = None  # None when the platform does not expose it
    duration_sec: int | None = None
    category: str = "General"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def engagement_rate(self) -> float:
        return (self.likes + self.comments + self.shares) / self.views if self.views else 0.0


class AccountSnapshot(BaseModel):
    platform: Platform
    account_label: str
    followers: int
    scopes: list[str] = []


class DataSource(BaseModel):
    """What the UI must always be able to show: where the numbers came from."""
    mode: Literal["demo", "live", "empty"]
    label: str
    platforms_live: list[str] = []
    platforms_demo: list[str] = []
