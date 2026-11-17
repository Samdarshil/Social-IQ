"""Gemini assistant tests against a MOCK Gemini server (tests/mock_gemini_server.py).

Real: the google-genai SDK, SocialIQ's tool loop, tool execution, cards, fallback logic.
Mock: the model's decisions. These tests prove the integration; real-Gemini behaviour needs a real key
(`python scripts/doctor.py --live`).
"""
import json
import os
import tempfile

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/g.db")

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.services.assistant_tools import TOOL_SCHEMAS, TOOLS
from app.services.llm import ToolSpec
from app.services.llm.gemini import GeminiProvider, to_gemini_schema
from tests.mock_gemini_server import EXPECTED_TOOLS, MockGemini

KEY = "test-key-NOT-A-REAL-KEY-123"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def demo(client):
    return {"Authorization": f"Bearer {client.post('/api/auth/demo').json()['token']}"}


@pytest.fixture()
def mock(monkeypatch):
    srv = MockGemini().start()
    s = get_settings()
    monkeypatch.setattr(s, "gemini_api_key", KEY)
    monkeypatch.setattr(s, "gemini_base_url", srv.url)
    monkeypatch.setattr(s, "llm_timeout_s", 5.0)
    yield srv
    srv.shutdown()


def ask(client, demo, q):
    r = client.post("/api/assistant/chat", headers=demo, json={"message": q})
    assert r.status_code == 200
    return r.json()


PROMPTS = [("Why did my engagement drop?", "analyze_engagement", "engagement_change"),
           ("Which platform is performing best?", "compare_platforms", "platform_comparison"),
           ("What should I post next?", "generate_content_strategy", "strategy"),
           ("Show my best-performing content.", "get_top_content", "top_content")]


@pytest.mark.parametrize("q,tool,card", PROMPTS)
def test_gemini_path_calls_real_tools_and_returns_cards(client, demo, mock, q, tool, card):
    r = ask(client, demo, q)
    assert r["mode"] == "llm" and r["provider"] == "gemini" and "Gemini" in r["mode_label"], r.get("notice")
    assert r["answer"].startswith("[MOCK-GEMINI]")
    assert [c["name"] for c in r["tool_calls"]] == [tool] and r["tool_calls"][0]["ok"]
    assert card in [c["type"] for c in r["cards"]]
    # floats from the model were coerced to the declared integer type
    for v in r["tool_calls"][0]["args"].values():
        assert isinstance(v, int) and not isinstance(v, bool)
    # what the SDK actually sent to the (mock) API
    first, second = mock.log[0], mock.log[1]
    assert first["key"] == KEY and first["path"].endswith(":generateContent")
    assert {d["name"] for d in first["body"]["tools"][0]["functionDeclarations"]} == EXPECTED_TOOLS
    assert any("functionResponse" in p for p in second["body"]["contents"][-1]["parts"])   # tool results went back to the model
    assert KEY not in json.dumps(r)                                                         # key never reaches the client


def test_engagement_numbers_reach_the_model(client, demo, mock):
    r = ask(client, demo, "Why did my engagement drop?")
    assert "engagement changed -" in r["answer"] and "significant=True" in r["answer"]


def test_tool_payloads_sent_to_gemini_contain_no_identifiers(client, demo, mock):
    for q, *_ in PROMPTS:
        ask(client, demo, q)
    sent = json.dumps([m["body"]["contents"] for m in mock.log if "contents" in m["body"]])
    for forbidden in ("novachen", "demo@socialiq.local", "access_token", "password", KEY):
        assert forbidden not in sent, forbidden


@pytest.mark.parametrize("mode,fragment", [("http500", "Gemini API error 500"), ("forbidden", "rejected the API key"),
                                           ("empty", "no usable content"), ("notool", "without using any SocialIQ tool")])
def test_failures_fall_back_visibly(client, demo, mock, mode, fragment):
    mock.mode = mode
    r = ask(client, demo, "Which platform is performing best?")
    assert r["mode"] == "local" and fragment in r["notice"], r
    assert r["cards"] and r["tool_calls"] and "[MOCK-GEMINI]" not in r["answer"]


def test_timeout_falls_back_within_budget(client, demo, mock, monkeypatch):
    import time
    monkeypatch.setattr(get_settings(), "llm_timeout_s", 1.0)
    mock.mode = "slow"
    t = time.monotonic()
    r = ask(client, demo, "Compare my platforms")
    assert r["mode"] == "local" and "timed out" in r["notice"] and time.monotonic() - t < 12


def test_unknown_tool_is_reported_then_recovers(client, demo, mock):
    mock.mode = "badtool"
    r = ask(client, demo, "anything")
    assert r["mode"] == "llm" and [(c["name"], c["ok"]) for c in r["tool_calls"]] == [("delete_everything", False), ("compare_platforms", True)]


def test_no_key_keeps_rule_based_router(client, demo, monkeypatch):
    monkeypatch.setattr(get_settings(), "gemini_api_key", "")
    r = ask(client, demo, "Why did my engagement drop?")
    assert r["mode"] == "local" and not r.get("notice") and "Rule-based" in r["mode_label"] and "GEMINI_API_KEY" in r["mode_label"]
    assert client.get("/api/health").json()["llm_configured"] is False


def test_health_and_privacy_report_gemini(client, demo, mock):
    assert client.get("/api/health").json() == {"status": "ok", "llm_configured": True, "llm_provider": "gemini"}
    ai = client.get("/api/privacy/overview", headers=demo).json()["ai"]
    assert ai["provider"] == "Google Gemini" and "Gemini" in ai["note"] and KEY not in json.dumps(ai)


def test_schema_adapter():
    assert to_gemini_schema({"type": "object", "additionalProperties": False, "properties": {"d": {"type": "integer", "minimum": 7, "default": 3}}}) == \
        {"type": "object", "properties": {"d": {"type": "integer", "minimum": 7}}}
    decls = GeminiProvider._declarations([ToolSpec.from_schema(t) for t in TOOL_SCHEMAS])
    assert {d.name for d in decls} == set(TOOLS) == EXPECTED_TOOLS and len(decls) == 13
    by = {d.name: d for d in decls}
    assert by["get_creator_profile"].parameters_json_schema is None           # parameterless tool: no schema sent
    assert by["predict_content_performance"].parameters_json_schema["required"] == ["platform", "category"]
