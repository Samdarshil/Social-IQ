# The Gemini-powered assistant

SocialIQ's Digital Assistant is powered by **Google Gemini** through the official `google-genai` Python SDK.
Gemini never produces analytics itself: it *chooses* SocialIQ's 13 tools, SocialIQ *executes* them on your data,
and Gemini writes the answer from the structured results. The same results are rendered as UI cards.

| Mode | When | How it works |
|---|---|---|
| **Gemini** | `GEMINI_API_KEY` is set | Function calling: Gemini selects tools, SocialIQ runs them, Gemini explains the results. |
| **Local** | No key, or Gemini fails / times out / returns something unusable | A deterministic router calls the same tools and composes the answer from their numbers. The UI says which mode answered and, on failure, why it fell back. |

## Enable

```bash
# backend/.env  (git-ignored; the key stays on the server)
GEMINI_API_KEY=your-key            # https://aistudio.google.com/apikey
GEMINI_MODEL=gemini-3.8-flash      # default; any Gemini model with function calling works
```

```bash
python scripts/doctor.py --live    # real call + a real function-calling probe
```

`GEMINI_MODEL` defaults to `gemini-3.8-flash`, the model Google's model page recommends for agentic use at the time of
writing. Model names change: if the doctor reports "model not found", pick a current one from
<https://ai.google.dev/gemini-api/docs/models>. `gemini-3.5-flash-lite` is the lower-latency, lower-cost option.

## Architecture (provider-agnostic)

```
assistant.py            owns the tools, system prompt, fallback; knows nothing about Gemini
  └─ services/llm/base.py     LLMProvider interface · ToolSpec · LLMError / LLMUnusable
       └─ services/llm/gemini.py   Gemini adapter (only file that imports google-genai)
assistant_tools.py      the 13 tools: single source of truth (JSON-Schema definitions)
```

To add another model, implement `LLMProvider.run(...)` and return it from `get_provider()`. Tools, cards, limits and
fallback are untouched.

### Gemini specifics handled by the adapter
- Tool schemas are sent as JSON Schema via `parameters_json_schema` (unsupported keywords stripped; tools with no parameters send none).
- Automatic function calling is **disabled**: SocialIQ executes tools itself so it can record them, apply limits and show cards.
- The model's own turn is appended back **unchanged** (this preserves Gemini 3 *thought signatures*, which Gemini 3 needs for correct tool use). Verified by a test that rejects a turn with the signature stripped.
- Integer arguments that arrive as floats (`30.0`) are coerced to the declared type before execution.
- All function responses for a model turn are returned in a single user message.
- Uses `models.generate_content` (stable). Google also offers a newer Interactions API; only `gemini.py` would change to adopt it.

## Failure handling (never faked)
Any of these produce the rule-based answer **plus a visible notice** saying why:
timeout (per-request `LLM_TIMEOUT_SECONDS`, whole-question `LLM_TOTAL_BUDGET_SECONDS`), HTTP errors, rejected key, quota,
empty or blocked response, tool-loop limit (5 rounds), and **an answer given without calling any tool** (the numbers would be unverifiable).

## What Gemini is allowed to see
Only what the tools return: aggregated metrics, platform names, categories, model scores, and post titles truncated to 80
characters when needed. Never sent: account handles or names, email, OAuth tokens, API secrets, passwords. Your question text is
sent to Google; the Privacy Center says so. Enforced in the tool layer and checked by `test_tool_payloads_sent_to_gemini_contain_no_identifiers`.

## Verification status
Automated tests run the **real SDK** and SocialIQ's real tool loop against a **mock Gemini server**
(`backend/tests/mock_gemini_server.py`, which labels every answer `[MOCK-GEMINI]`). They prove request/response handling,
tool execution, cards, signature echo, data minimisation and every fallback path. They do **not** prove how real Gemini picks tools.
That requires your key: run `python scripts/doctor.py --live`, then ask the five suggested prompts and confirm each shows
`Used: <tool names>` above the answer and a mode line reading `Gemini (<model>) using SocialIQ tools`.
