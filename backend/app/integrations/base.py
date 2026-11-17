"""Common provider-adapter interface. Each platform connects independently.

Honesty rules baked in:
  * `is_configured()` is False without real credentials: the UI then shows "Not configured" and
    never a fake "Connected".
  * Adapters request read-only scopes only.
  * Adapters raise ProviderUnavailable when the platform API cannot supply something.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.schemas.content import AccountSnapshot, Content


class ProviderUnavailable(Exception):
    """The platform/API cannot provide this right now (missing credentials, API tier, permissions)."""


@dataclass
class TokenSet:
    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None
    scopes: list[str] | None = None


class ProviderAdapter(ABC):
    platform: str
    label: str
    read_only_scopes: list[str]
    # Plain-language notes shown in the Privacy Center / connect modal
    api_notes: str = ""
    uses_pkce: bool = False

    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    def authorization_url(self, state: str, redirect_uri: str, code_challenge: str | None = None) -> str: ...

    @abstractmethod
    def exchange_code(self, code: str, redirect_uri: str, code_verifier: str | None = None) -> TokenSet: ...

    @abstractmethod
    def fetch_account(self, tokens: TokenSet) -> AccountSnapshot: ...

    @abstractmethod
    def fetch_content(self, tokens: TokenSet, limit: int = 100) -> list[Content]: ...

    def refresh(self, tokens: TokenSet) -> TokenSet:
        raise ProviderUnavailable(f"{self.label} token refresh is not supported; please reconnect.")

    def describe(self) -> dict:
        return {
            "platform": self.platform,
            "label": self.label,
            "configured": self.is_configured(),
            "scopes": self.read_only_scopes,
            "notes": self.api_notes,
        }
