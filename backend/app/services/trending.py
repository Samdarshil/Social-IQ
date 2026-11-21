"""Loads YouTube trending data (Kaggle: datasnaek/youtube-new) and serves clustering results.

Resolution order for a country:
  1. Raw CSV in YT_TRENDING_DIR (default backend/data/kaggle_youtube/): `<CC>videos.csv` or `<CC>videos_1.csv`. Computed live, cached.
  2. Pre-computed snapshot committed in app/ml/snapshots/ (built by scripts/build_trending_snapshots.py from the same CSVs).
The response states which one was used. The raw CSVs are not committed to the repository (size and Kaggle terms).
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from app.config import BASE_DIR
from app.ml import clustering

SNAP_DIR = BASE_DIR / "app" / "ml" / "snapshots"
COUNTRIES = {"US": "United States", "GB": "United Kingdom", "CA": "Canada", "DE": "Germany", "FR": "France", "IN": "India",
             "JP": "Japan", "KR": "South Korea", "MX": "Mexico", "RU": "Russia"}


def raw_dir() -> Path:
    return Path(os.getenv("YT_TRENDING_DIR") or BASE_DIR / "data" / "kaggle_youtube")


def raw_csv(cc: str) -> Path | None:
    for name in (f"{cc}videos.csv", f"{cc}videos_1.csv"):
        p = raw_dir() / name
        if p.exists():
            return p
    return None


@lru_cache
def category_map(cc: str | None = None) -> dict[int, str]:
    out = {int(k): v for k, v in json.loads((SNAP_DIR / "categories.json").read_text()).items()}
    if cc:
        p = raw_dir() / f"{cc}_category_id.json"
        if p.exists():
            out.update({int(i["id"]): i["snippet"]["title"] for i in json.loads(p.read_text())["items"]})
    return out


def snapshot(cc: str) -> dict | None:
    p = SNAP_DIR / f"yt_trending_{cc}.json"
    return json.loads(p.read_text()) if p.exists() else None


@lru_cache(maxsize=16)
def compute(cc: str) -> dict:
    csv = raw_csv(cc)
    res = clustering.analyse(clustering.read_csv(csv), category_map(cc), cc)
    res["source"] = dict(kind="raw_csv", file=csv.name)
    return res


def get(cc: str) -> dict | None:
    cc = cc.upper()
    if cc not in COUNTRIES:
        return None
    res = compute(cc) if raw_csv(cc) else snapshot(cc)
    if res is None:
        return None
    if res.get("source", {}).get("kind") != "raw_csv":
        res = {**res, "source": dict(kind="snapshot", note="Pre-computed from the Kaggle CSV with the same code. Place the CSV in backend/data/kaggle_youtube/ to recompute live.")}
    res["country_name"] = COUNTRIES[cc]
    return res


def countries() -> list[dict]:
    idx = SNAP_DIR / "index.json"
    base = {r["country"]: r for r in json.loads(idx.read_text())} if idx.exists() else {}
    out = []
    for cc, name in COUNTRIES.items():
        if cc in base or raw_csv(cc):
            out.append(dict(country=cc, name=name, **{k: v for k, v in base.get(cc, {}).items() if k != "country"}))
    return out
