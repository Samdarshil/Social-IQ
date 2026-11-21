"""Integration tests that run WITHOUT real credentials by faking the remote servers.

What this proves: our request construction, state/CSRF handling, token encryption, normalization into the
unified schema, and disconnect/delete behaviour. What it does NOT prove: that Google accepts our
real credentials. See docs/YOUTUBE_SETUP.md and scripts/doctor.py for the live check.
"""
import json
import os
import tempfile
from urllib.parse import parse_qs, urlparse

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/i.db")

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import SessionLocal
from app.main import app
from app.models.tables import PlatformConnection
from app.security.crypto import decrypt_token


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _user(client, email):
    r = client.post("/api/auth/register", json={"email": email, "password": "correct-horse-1", "display_name": "T"})
    return {"Authorization": f"Bearer {r.json()['token']}"}


class _Resp:
    def __init__(self, code, body):
        self.status_code, self._b = code, body

    def json(self):
        return self._b


def _fake_google(monkeypatch):
    def post(url, data=None, **kw):
        assert url == "https://oauth2.googleapis.com/token" and data["grant_type"] in ("authorization_code", "refresh_token")
        return _Resp(200, {"access_token": "ACCESS-123", "refresh_token": "REFRESH-456", "expires_in": 3600,
                           "scope": "https://www.googleapis.com/auth/youtube.readonly"})

    def get(url, params=None, headers=None, **kw):
        assert headers["Authorization"] == "Bearer ACCESS-123"
        if url.endswith("/channels") and "snippet" in params["part"]:
            return _Resp(200, {"items": [{"snippet": {"title": "Test Channel"}, "statistics": {"subscriberCount": "4321"}}]})
        if url.endswith("/channels"):
            return _Resp(200, {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU1"}}}]})
        if url.endswith("/playlistItems"):
            return _Resp(200, {"items": [{"contentDetails": {"videoId": f"v{i}"}} for i in range(3)]})
        if url.endswith("/videos"):
            return _Resp(200, {"items": [
                {"id": "v0", "snippet": {"title": "How to build RAG step by step", "publishedAt": "2026-10-01T10:00:00Z", "description": ""},
                 "statistics": {"viewCount": "1000", "likeCount": "80", "commentCount": "10"}, "contentDetails": {"duration": "PT10M30S"}},
                {"id": "v1", "snippet": {"title": "Quick tip", "publishedAt": "2026-10-05T12:00:00Z"},
                 "statistics": {"viewCount": "500", "likeCount": "30", "commentCount": "2"}, "contentDetails": {"duration": "PT45S"}},
                {"id": "v2", "snippet": {"title": "Q&A answering your questions", "publishedAt": "2026-10-09T09:00:00Z"},
                 "statistics": {"viewCount": "700"}, "contentDetails": {"duration": "PT1H2M"}}]})
        raise AssertionError(f"unexpected GET {url}")

    monkeypatch.setattr("httpx.post", post)
    monkeypatch.setattr("httpx.get", get)


def test_youtube_full_flow(client, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "google_client_id", "cid")
    monkeypatch.setattr(s, "google_client_secret", "sec")
    h = _user(client, "yt@example.com")

    # platform list now reports YouTube as connectable, others still not configured (honest status)
    st = {p["platform"]: p["status"] for p in client.get("/api/platforms", headers=h).json()}
    assert st["youtube"] == "available" and st["instagram"] == "not_configured"

    url = client.post("/api/connect/youtube/start", headers=h).json()["authorization_url"]
    q = parse_qs(urlparse(url).query)
    assert q["scope"] == ["https://www.googleapis.com/auth/youtube.readonly"]  # read-only, nothing else
    assert q["client_id"] == ["cid"] and "client_secret" not in url
    assert q["redirect_uri"][0].endswith("/api/connect/youtube/callback")

    # tampered / wrong-platform / missing state is rejected
    assert client.get("/api/connect/youtube/callback?code=x&state=garbage", follow_redirects=False).status_code == 400
    other = client.post("/api/connect/youtube/start", headers=h).json()["authorization_url"]
    assert parse_qs(urlparse(other).query)["state"][0] != ""

    _fake_google(monkeypatch)
    state = q["state"][0]
    r = client.get(f"/api/connect/youtube/callback?code=abc&state={state}", follow_redirects=False)
    assert r.status_code in (302, 307)
    loc = parse_qs(urlparse(r.headers["location"]).query)
    assert loc["connected"] == ["youtube"] and loc["synced"] == ["3"]

    # live workspace, normalized into the unified schema, clearly not demo
    src = client.get("/api/source", headers=h).json()
    assert src["source"]["mode"] == "live" and src["posts"] == 3
    items = client.get("/api/content?sort=views", headers=h).json()["items"]
    assert {i["content_type"] for i in items} == {"video", "short"} and items[0]["views"] == 1000
    assert any(i["category"] == "Tutorials" for i in items) and any(i["category"] == "Q&A" for i in items)
    assert client.get("/api/summary?days=180", headers=h).json()["current"]["posts"] == 3

    # tokens are encrypted at rest and round-trip
    with SessionLocal() as db:
        c = db.query(PlatformConnection).filter_by(platform="youtube").first()
        assert "ACCESS-123" not in c.access_token_enc and "REFRESH-456" not in c.refresh_token_enc
        assert decrypt_token(c.access_token_enc) == "ACCESS-123" and decrypt_token(c.refresh_token_enc) == "REFRESH-456"

    # ML refuses honestly on tiny live data rather than faking a model
    r = client.post("/api/ml/predict", headers=h, json=dict(platform="youtube", category="Tutorials", content_type="video", publish_at="2026-11-20T10:00:00Z"))
    assert r.status_code == 422 and "at least" in r.json()["detail"]

    # privacy: export omits tokens; disconnect removes tokens and content
    exp = json.dumps(client.get("/api/privacy/export", headers=h).json())
    assert "ACCESS-123" not in exp and "REFRESH-456" not in exp and "Test Channel" in exp
    d = client.delete("/api/connections/youtube", headers=h).json()
    assert d["content_removed"] == 3
    with SessionLocal() as db:
        assert db.query(PlatformConnection).filter_by(platform="youtube").count() == 0
    assert client.get("/api/source", headers=h).json()["source"]["mode"] == "empty"


def test_failed_exchange_leaves_no_fake_connection(client, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "google_client_id", "cid")
    monkeypatch.setattr(s, "google_client_secret", "sec")
    h = _user(client, "fail@example.com")
    state = parse_qs(urlparse(client.post("/api/connect/youtube/start", headers=h).json()["authorization_url"]).query)["state"][0]
    monkeypatch.setattr("httpx.post", lambda *a, **k: _Resp(400, {"error": "invalid_grant"}))
    r = client.get(f"/api/connect/youtube/callback?code=bad&state={state}", follow_redirects=False)
    assert "error=" in r.headers["location"]
    assert client.get("/api/source", headers=h).json()["source"]["mode"] == "empty"


def test_linkedin_refuses_to_fabricate(client, monkeypatch):
    from app.integrations.base import ProviderUnavailable
    from app.integrations.registry import get_adapter
    with pytest.raises(ProviderUnavailable):
        get_adapter("linkedin").fetch_content(None)
