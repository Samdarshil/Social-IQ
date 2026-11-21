import os, tempfile
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/t.db"
os.environ.pop("GEMINI_API_KEY", None)

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security.crypto import decrypt_token, encrypt_token, hash_password, verify_password


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def demo(client):
    r = client.post("/api/auth/demo"); assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_requires_auth(client):
    assert client.get("/api/summary").status_code == 401


def test_register_login_and_empty_workspace(client):
    r = client.post("/api/auth/register", json={"email": "a@b.co", "password": "correct-horse-1", "display_name": "A"})
    assert r.status_code == 200
    h = {"Authorization": f"Bearer {r.json()['token']}"}
    assert client.post("/api/auth/login", json={"email": "a@b.co", "password": "wrong-password"}).status_code == 401
    assert client.get("/api/source", headers=h).json()["source"]["mode"] == "empty"
    assert client.get("/api/summary", headers=h).status_code == 200
    assert client.get("/api/platforms/compare", headers=h).json()["platforms"] == []
    assert client.post("/api/ml/predict", headers=h, json=dict(platform="youtube", category="Tutorials", content_type="video", publish_at="2026-11-20T10:00:00Z")).status_code == 422
    chat = client.post("/api/assistant/chat", headers=h, json={"message": "why did my engagement drop?"}).json()
    assert "no data" in chat["answer"].lower()
    assert client.post("/api/connect/youtube/start", headers=h).status_code == 503  # not configured: honest error
    assert client.delete("/api/privacy/data", headers=h).json()["content_deleted"] == 0


def test_weak_password_rejected(client):
    assert client.post("/api/auth/register", json={"email": "x@y.co", "password": "short"}).status_code == 422


def test_demo_is_labelled_and_cannot_connect(client, demo):
    assert client.get("/api/source", headers=demo).json()["source"]["mode"] == "demo"
    assert client.post("/api/connect/youtube/start", headers=demo).status_code == 409
    assert all(p["status"] == "demo" for p in client.get("/api/platforms", headers=demo).json())
    assert client.get("/api/privacy/export", headers=demo).status_code == 409


def test_analytics_endpoints(client, demo):
    s = client.get("/api/summary?days=30", headers=demo).json()
    assert s["current"]["views"] > 0 and s["source"]["mode"] == "demo"
    assert len(client.get("/api/platforms/compare", headers=demo).json()["platforms"]) == 4
    assert client.get("/api/platforms/compare?platforms=youtube", headers=demo).json()["platforms"][0]["platform"] == "youtube"
    assert client.get("/api/timeseries?freq=W", headers=demo).json()["points"]
    ex = client.get("/api/engagement-change", headers=demo).json()
    assert ex["available"] and ex["change_pct"] < 0 and ex["significant"]
    for path in ("best-times", "categories", "engagement-breakdown", "anomalies", "cross-platform", "profile", "insights", "content/top"):
        assert client.get(f"/api/{path}", headers=demo).status_code == 200, path


def test_input_validation(client, demo):
    bad = dict(platform="youtube", category="Tutorials", content_type="reel", publish_at="2026-11-20T10:00:00Z")
    assert client.post("/api/ml/predict", headers=demo, json=bad).status_code == 422
    assert client.post("/api/ml/predict", headers=demo, json={**bad, "content_type": "video", "category": "Nope"}).status_code == 422
    assert client.get("/api/summary?days=99999", headers=demo).status_code == 422


def test_prediction_and_explanation(client, demo):
    body = dict(title="How to build RAG in 20 minutes?", platform="youtube", category="Tutorials", content_type="video", duration_sec=600,
                publish_at="2026-11-20T17:00:00Z")
    r = client.post("/api/ml/predict", headers=demo, json=body).json()
    assert 0 <= r["score"] <= 100 and r["label"] in {"LOW", "MEDIUM", "HIGH"}
    assert r["interval"]["low"] <= r["score"] <= r["interval"]["high"]
    assert r["explanation"]["positive"] or r["explanation"]["negative"]
    # prediction responds to inputs (not a constant)
    r2 = client.post("/api/ml/predict", headers=demo, json={**body, "platform": "x", "content_type": "post", "category": "Opinions", "duration_sec": None}).json()
    assert r2["score"] != r["score"]
    mc = client.get("/api/ml/model-card", headers=demo).json()
    assert mc["selected_model"] in {"RandomForest", "GradientBoosting", "XGBoost"} and mc["test"]["mae"] > 0
    assert mc["split"].startswith("Chronological") and 0 <= mc["interval"]["empirical_test_coverage"] <= 1


def test_assistant_uses_tools(client, demo):
    for q, tool in [("Why did my engagement drop?", "analyze_engagement"), ("Which platform is performing best?", "compare_platforms"),
                    ("What should I post next?", "generate_content_strategy"), ("Show my best-performing content", "get_top_content")]:
        r = client.post("/api/assistant/chat", headers=demo, json={"message": q}).json()
        assert tool in [c["name"] for c in r["tool_calls"]], q
        assert r["cards"] and r["mode"] == "local" and r["source"]["mode"] == "demo"


def test_no_target_leakage():
    from app.ml.features import build_training_frame
    from app.services.dataset import demo_workspace
    ws = demo_workspace()
    f = build_training_frame(ws)
    # history features for the very first post of each platform must be empty (nothing came before it)
    first = f.sort_values("published_at").groupby("platform").head(1)
    assert first["h_cat_n"].eq(0).all() and first["h_logviews_10"].isna().all()
    # perturbing a post's own engagement must not change its own features
    ws2 = demo_workspace()
    i = len(ws2.content) // 2
    cid = ws2.content.loc[i, "content_id"]
    ws2.content.loc[i, ["views", "likes"]] = [10, 1]; ws2.content.loc[i, "engagement_rate"] = 0.1
    f2 = build_training_frame(ws2)
    a, b = f[f.content_id == cid].iloc[0], f2[f2.content_id == cid].iloc[0]
    for c in ("h_logviews_10", "h_er_10", "h_cat_er", "c_er_10"):
        assert (pd.isna(a[c]) and pd.isna(b[c])) or a[c] == b[c], c


def test_crypto():
    t = encrypt_token("secret-token"); assert t != "secret-token" and decrypt_token(t) == "secret-token"
    h = hash_password("hunter2hunter2"); assert verify_password("hunter2hunter2", h) and not verify_password("x", h)


def test_security_headers_and_privacy(client, demo):
    r = client.get("/api/health"); assert r.headers["x-content-type-options"] == "nosniff"
    ov = client.get("/api/privacy/overview", headers=demo).json()
    assert "Social-media passwords" in ov["never_stores"] and ov["security"]["not_claimed"]
