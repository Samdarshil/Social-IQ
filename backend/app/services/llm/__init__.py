from __future__ import annotations

from app.config import get_settings
from app.services.llm.base import LLMError, LLMProvider, LLMResult, LLMUnusable, ToolSpec

__all__ = ["get_provider", "LLMError", "LLMProvider", "LLMResult", "LLMUnusable", "ToolSpec"]


def get_provider() -> LLMProvider | None:
    """Returns the configured provider, or None when no API key is set (assistant then uses the local router)."""
    s = get_settings()
    if s.gemini_api_key:
        from app.services.llm.gemini import GeminiProvider
        return GeminiProvider(s.gemini_api_key, s.gemini_model, timeout_s=s.llm_timeout_s,
                              total_budget_s=s.llm_total_budget_s, base_url=s.gemini_base_url or None)
    return None
