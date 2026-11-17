from __future__ import annotations

from app.integrations.base import ProviderAdapter
from app.integrations.others import InstagramAdapter, LinkedInAdapter, XAdapter
from app.integrations.youtube import YouTubeAdapter

ADAPTERS: dict[str, ProviderAdapter] = {
    a.platform: a for a in (YouTubeAdapter(), InstagramAdapter(), XAdapter(), LinkedInAdapter())
}


def get_adapter(platform: str) -> ProviderAdapter:
    if platform not in ADAPTERS:
        raise KeyError(platform)
    return ADAPTERS[platform]
