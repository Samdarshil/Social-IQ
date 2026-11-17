#!/usr/bin/env python3
"""SocialIQ configuration doctor. Run from the repo root:  python scripts/doctor.py [--live]

Reports which integrations are configured and prints the exact redirect URIs to register.
--live additionally calls the real Gemini API twice (a plain reply, then a function-calling probe) to verify your key, model
and tool calling. It never prints secrets.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import get_settings  # noqa: E402
from app.integrations.registry import ADAPTERS  # noqa: E402

OK, NO = "\033[32m✔\033[0m", "\033[33m–\033[0m"


def main() -> int:
    s = get_settings()
    print(f"\nSocialIQ doctor  (env={s.env})\n")
    print("Platform OAuth")
    for p, a in ADAPTERS.items():
        print(f"  {OK if a.is_configured() else NO} {a.label:10} {'configured' if a.is_configured() else 'not configured: demo mode only for this platform'}")
        print(f"      redirect URI to register: {s.backend_url}/api/connect/{p}/callback")
        print(f"      scopes requested (read-only): {', '.join(a.read_only_scopes)}")
    print("\nAI assistant (Google Gemini)")
    print(f"  {OK if s.gemini_api_key else NO} GEMINI_API_KEY {'set' if s.gemini_api_key else 'not set: built-in rule-based router will answer'} (model: {s.gemini_model})")
    if s.gemini_base_url:
        print(f"  ! GEMINI_BASE_URL is set to {s.gemini_base_url}: requests go there, not to Google")
    print("\nSecurity")
    print(f"  {OK if s.is_production else NO} SOCIALIQ_ENV={s.env}")
    https = s.backend_url.startswith("https://")
    print(f"  {OK if https else NO} BACKEND_URL {'uses HTTPS' if https else 'is not HTTPS (fine for local dev, required in production)'}")
    if s.is_production and not https:
        print("  ! production without HTTPS: OAuth providers will reject non-HTTPS redirect URIs")

    if "--live" in sys.argv:
        print("\nLive Gemini check")
        if not s.gemini_api_key:
            print("  set GEMINI_API_KEY first")
            return 1
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=s.gemini_api_key, http_options=types.HttpOptions(timeout=30000, **({"base_url": s.gemini_base_url} if s.gemini_base_url else {})))
            r = client.models.generate_content(model=s.gemini_model, contents="Reply with the single word: ready")
            print(f"  {OK} {s.gemini_model} replied: {(r.text or '').strip()!r}")
            tool = types.Tool(function_declarations=[types.FunctionDeclaration(
                name="compare_platforms", description="Compare the user's social platforms over the last N days.",
                parameters_json_schema={"type": "object", "properties": {"days": {"type": "integer"}}})])
            cfg = types.GenerateContentConfig(tools=[tool], automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
            r = client.models.generate_content(model=s.gemini_model, contents="Which of my platforms is performing best over the last 30 days?", config=cfg)
            calls = r.function_calls or []
            if calls and calls[0].name == "compare_platforms":
                print(f"  {OK} function calling works: model called {calls[0].name}({dict(calls[0].args or {})})")
            else:
                print(f"  ✘ the model did not call the tool (got: {(r.text or '')[:80]!r}). Try another GEMINI_MODEL.")
                return 1
        except Exception as e:  # noqa: BLE001
            print(f"  ✘ call failed: {type(e).__name__}: {str(e)[:200]}")
            return 1
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
