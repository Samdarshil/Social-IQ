"""Gemini adapter (official `google-genai` SDK, `models.generate_content`).

Function calling is driven manually (automatic function calling disabled) so SocialIQ executes its own
tools, records them for the UI, and enforces limits. Notes on the Gemini wire format handled here:
  * Tool schemas are passed as JSON Schema via `parameters_json_schema`; tools without parameters omit it.
  * The model's own `Content` (including any thought signatures) is appended back to the conversation
    UNCHANGED before the function responses: Gemini 3 models require this for correct tool use.
  * Function arguments can arrive as floats (30.0): coercion to the declared integer type happens in the
    assistant's executor, not here.
  * All function responses for one model turn go back in a single user `Content`.
"""
from __future__ import annotations

import json
import time
from typing import Any

from app.services.llm.base import Executor, LLMError, LLMProvider, LLMResult, LLMUnusable, ToolSpec

_ALLOWED_SCHEMA_KEYS = {"type", "properties", "required", "description", "enum", "items", "minimum", "maximum"}
MAX_TOOL_RESPONSE_CHARS = 12000


def to_gemini_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Reduce a JSON Schema to the subset Gemini accepts (drops unsupported keywords recursively)."""
    out: dict[str, Any] = {}
    for k, v in schema.items():
        if k not in _ALLOWED_SCHEMA_KEYS:
            continue
        if k == "properties":
            out[k] = {name: to_gemini_schema(p) for name, p in v.items()}
        elif k == "items":
            out[k] = to_gemini_schema(v)
        else:
            out[k] = v
    return out


def _json_safe(data: Any) -> Any:
    return json.loads(json.dumps(data, default=str))


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout_s: float = 20.0, total_budget_s: float = 45.0,
                 base_url: str | None = None, client: Any = None) -> None:
        self.model = model
        self.timeout_s = timeout_s
        self.total_budget_s = total_budget_s
        if client is not None:               # tests / custom clients
            self._client = client
            return
        from google import genai
        from google.genai import types
        http = dict(timeout=int(timeout_s * 1000), retry_options=types.HttpRetryOptions(attempts=2, initial_delay=0.5, max_delay=2.0))
        if base_url:
            http["base_url"] = base_url
        self._client = genai.Client(api_key=api_key, http_options=types.HttpOptions(**http))

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _declarations(tools: list[ToolSpec]):
        from google.genai import types
        decls = []
        for t in tools:
            params = to_gemini_schema(t.parameters)
            kwargs: dict[str, Any] = dict(name=t.name, description=t.description)
            if params.get("properties"):
                kwargs["parameters_json_schema"] = params
            decls.append(types.FunctionDeclaration(**kwargs))
        return decls

    @staticmethod
    def _wrap_error(exc: Exception) -> LLMError:
        """Translate SDK/network errors into safe, secret-free messages."""
        name = type(exc).__name__
        code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
        low = f"{name} {exc}".lower()
        if "timeout" in low or "timed out" in low:
            return LLMError("Gemini timed out")
        if code in (401, 403) or "api key" in low or "permission" in low:
            return LLMError("Gemini rejected the API key or permissions")
        if code == 429 or "quota" in low or "resource_exhausted" in low:
            return LLMError("Gemini quota or rate limit reached")
        if isinstance(code, int):
            return LLMError(f"Gemini API error {code}")
        return LLMError(f"Gemini request failed ({name})")

    # ------------------------------------------------------------------ main loop
    def run(self, *, system: str, history: list[dict[str, str]], message: str, tools: list[ToolSpec],
            execute: Executor, max_rounds: int = 5) -> LLMResult:
        from google.genai import types

        contents: list[Any] = []
        for h in history:
            if h.get("content") and h.get("role") in ("user", "assistant"):
                contents.append(types.Content(role="user" if h["role"] == "user" else "model", parts=[types.Part.from_text(text=h["content"])]))
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=message)]))

        config = types.GenerateContentConfig(
            system_instruction=system, temperature=0.2, max_output_tokens=2048,
            tools=[types.Tool(function_declarations=self._declarations(tools))],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))

        deadline = time.monotonic() + self.total_budget_s
        for round_no in range(1, max_rounds + 1):
            if time.monotonic() > deadline:
                raise LLMError("Gemini exceeded the time budget")
            try:
                resp = self._client.models.generate_content(model=self.model, contents=contents, config=config)
            except Exception as exc:  # noqa: BLE001 - SDK raises many types; all become a safe LLMError
                raise self._wrap_error(exc) from None

            cands = getattr(resp, "candidates", None) or []
            if not cands or cands[0].content is None or not (cands[0].content.parts or []):
                block = getattr(getattr(resp, "prompt_feedback", None), "block_reason", None)
                reason = getattr(cands[0], "finish_reason", None) if cands else None
                raise LLMUnusable(f"Gemini returned no usable content ({block or reason or 'empty response'})")

            calls = list(resp.function_calls or [])
            if calls:
                contents.append(cands[0].content)       # echo model turn unchanged (keeps thought signatures)
                parts = []
                for fc in calls:
                    result = execute(fc.name, dict(fc.args or {}))
                    payload = {"error": result["error"]} if isinstance(result, dict) and "error" in result else {"result": _json_safe(result)}
                    if len(json.dumps(payload)) > MAX_TOOL_RESPONSE_CHARS:
                        payload = {"result_truncated": json.dumps(payload)[:MAX_TOOL_RESPONSE_CHARS]}
                    parts.append(types.Part.from_function_response(name=fc.name, response=payload))
                contents.append(types.Content(role="user", parts=parts))
                continue

            text = "".join(p.text for p in cands[0].content.parts if getattr(p, "text", None) and not getattr(p, "thought", False)).strip()
            if not text:
                raise LLMUnusable("Gemini returned an empty answer")
            return LLMResult(answer=text, provider=self.name, model=self.model, rounds=round_no)

        raise LLMUnusable("Gemini did not finish within the tool-call limit")
