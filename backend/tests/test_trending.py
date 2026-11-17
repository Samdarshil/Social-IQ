"""Clustering pipeline tests on a small synthetic file in the Kaggle schema (the real CSVs are not in the repo)."""
import os
import tempfile

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/t.db")

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml import clustering
from app.services import trending

CATS = {10: "Music", 22: "People & Blogs", 25: "News & Politics"}


def make_raw(n=900, seed=1) -> pd.DataFrame:
    rng = np.random.RandomState(seed)
    tier = rng.choice(3, n, p=[.3, .45, .25])
    views = np.exp(rng.normal([9, 12, 15][0], 0.5, n) + np.array([0, 3, 6])[tier])
    er = np.array([.01, .03, .05])[tier] * np.exp(rng.normal(0, .25, n))
    likes = (views * er * .85).astype(int)
    comments = (views * er * .15).astype(int)
    df = pd.DataFrame(dict(video_id=[f"v{i}" for i in range(n)], trending_date="18.14.01", title="t", channel_title="c",
                           category_id=rng.choice(list(CATS), n), publish_time="2018-01-10T10:00:00.000Z", tags="a|b",
                           views=views.astype(int), likes=likes, dislikes=(likes * .05).astype(int), comment_count=comments,
                           comments_disabled=False, ratings_disabled=False, video_error_or_removed=False))
    return df


def test_dedupe_and_exclusions():
    raw = make_raw(400)
    dup = raw.iloc[:50].copy(); dup["views"] = dup["views"] // 2          # earlier, lower-view snapshots of the same videos
    raw.loc[:9, "comments_disabled"] = True
    raw.loc[10:12, "video_error_or_removed"] = True
    d, acct = clustering.prepare(pd.concat([raw, dup]))
    assert acct["rows_raw"] == 450 and acct["videos_unique"] == 400
    assert acct["excluded"]["comments_or_ratings_disabled"] == 10 and acct["excluded"]["removed_or_error"] == 3
    assert len(d) == acct["videos_used"] == 387
    kept = d.set_index("video_id").loc["v20", "views"]
    assert kept == raw.set_index("video_id").loc["v20", "views"]          # latest (highest cumulative) snapshot kept


def test_analyse_structure_and_ordering():
    res = clustering.analyse(make_raw(), CATS, "XX")
    cl = res["clusters"]
    assert [c["label"] for c in cl] == ["Lower engagement", "Moderate engagement", "Higher engagement"]
    assert sum(c["size"] for c in cl) == res["dataset"]["videos_used"]
    v = [c["medians"]["views"] for c in cl]
    assert v == sorted(v)                                                   # tiers ordered
    m = res["model"]
    assert set(m["silhouette_by_k"]) == {2, 3, 4, 5, 6, 7, 8} and -1 <= m["silhouette"] <= 1
    assert 0.5 < m["stability_ari_mean"] <= 1                               # well-separated synthetic data is stable
    assert res["correlations"]["spearman"][0][1] > 0.8                      # views ~ likes
    assert res["category"]["kruskal"] is not None and res["scatter"]["points"]
    assert any("not predictions" in c for c in res["caveats"])


def test_requires_enough_data():
    with pytest.raises(ValueError):
        clustering.analyse(make_raw(100), CATS, "XX")


def test_deterministic():
    a, b = clustering.analyse(make_raw(), CATS, "XX"), clustering.analyse(make_raw(), CATS, "XX")
    assert a["clusters"][0]["size"] == b["clusters"][0]["size"] and a["model"]["silhouette"] == b["model"]["silhouette"]


def test_api_serves_snapshots_and_requires_auth():
    with TestClient(app) as c:
        assert c.get("/api/research/trending/US").status_code == 401
        tok = c.post("/api/auth/demo").json()["token"]
        h = {"Authorization": f"Bearer {tok}"}
        r = c.get("/api/research/trending/US", headers=h)
        assert r.status_code == 200
        j = r.json()
        assert j["country"] == "US" and len(j["clusters"]) == 3 and j["source"]["kind"] in ("snapshot", "raw_csv")
        assert {"Lower engagement", "Higher engagement"} <= {x["label"] for x in j["clusters"]}
        assert c.get("/api/research/trending/ZZ", headers=h).status_code == 404
        assert len(c.get("/api/research/trending/countries", headers=h).json()["items"]) >= 1


def test_raw_csv_path_used_when_present(tmp_path, monkeypatch):
    make_raw(900).to_csv(tmp_path / "XXvideos.csv", index=False)
    monkeypatch.setenv("YT_TRENDING_DIR", str(tmp_path))
    monkeypatch.setitem(trending.COUNTRIES, "XX", "Testland")
    trending.compute.cache_clear()
    res = trending.get("XX")
    assert res["source"]["kind"] == "raw_csv" and res["dataset"]["videos_used"] == 900
    trending.compute.cache_clear()
