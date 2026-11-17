"""Provider-agnostic LLM interface for the SocialIQ assistant.

The assistant owns the tools (app/services/assistant_tools.py). A provider only has to:
  1. show the tool definitions to its model,
  2. run the model's tool calls through the `execute` callback it is given,
  3. return the final text.
To add another LLM, implement `LLMProvider.run` and register it in `__init__.get_provider`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable


class LLMError(Exception):
    """The provider failed (network, timeout, auth, quota). Message is safe to show: never contains secrets."""


class LLMUnusable(LLMError):
    """The provider answered but the response cannot be used (empty, blocked, tool-loop limit)."""


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]          # JSON Schema (object)

    @classmethod
    def from_schema(cls, d: dict[str, Any]) -> "ToolSpec":
        """Build from SocialIQ's tool definition dicts (name / description / input_schema)."""
        return cls(d["name"], d["description"], d.get("input_schema") or {"type": "object", "properties": {}})


# execute(name, args) -> the tool result's JSON-safe `data` payload (what the model may see)
Executor = Callable[[str, dict[str, Any]], dict[str, Any]]


@dataclass
class LLMResult:
    answer: str
    provider: str
    model: str
    rounds: int = 1
    notes: list[str] = field(default_factory=list)


class LLMProvider(ABC):
    name: str
    model: str

    @abstractmethod
    def run(self, *, system: str, history: list[dict[str, str]], message: str, tools: list[ToolSpec],
            execute: Executor, max_rounds: int = 5) -> LLMResult: ...
