"""Leakage-safe feature engineering.

Every history feature for a post is computed ONLY from posts on the same platform that were published
strictly before it. Target references (percentile curves) are fit on training rows only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.schemas.content import CATEGORIES, CONTENT_TYPES, PLATFORMS
from app.utils.categorize import title_features

ALL_CATEGORIES = CATEGORIES + ["General"]
ALL_TYPES = sorted({t for v in CONTENT_TYPES.values() for t in v})

NUMERIC = ["hour", "dow", "is_weekend", "duration_sec", "has_duration", "title_len", "title_words", "has_question",
           "has_number", "has_emoji", "hashtags", "is_caps_heavy", "followers_log",
           "h_logviews_10", "h_er_10", "h_er_trend", "h_cat_er", "h_cat_logviews", "h_cat_n", "h_gap_days", "h_posts_30d", "c_er_10", "c_er_ratio", "c_logviews_ratio"]
HISTORY = ["h_logviews_10", "h_er_10", "h_er_trend", "h_cat_er", "h_cat_logviews", "h_cat_n", "h_gap_days", "h_posts_30d"]
CREATOR = ["c_er_10", "c_er_ratio", "c_logviews_ratio"]

# Human-readable groups used when explaining predictions
GROUPS = {
    "Publishing time": ["hour", "dow", "is_weekend"],
    "Platform": [f"platform_{p}" for p in PLATFORMS],
    "Format": [f"type_{t}" for t in ALL_TYPES] + ["duration_sec", "has_duration"],
    "Topic category": [f"cat_{c}" for c in ALL_CATEGORIES],
    "Title style": ["title_len", "title_words", "has_question", "has_number", "has_emoji", "hashtags", "is_caps_heavy"],
    "Audience size": ["followers_log"],
    "Recent reach on this platform": ["h_logviews_10"],
    "Recent engagement on this platform": ["h_er_10"],
    "Engagement trend": ["h_er_trend", "c_er_10", "c_er_ratio", "c_logviews_ratio"],
    "Track record in this category": ["h_cat_er", "h_cat_logviews", "h_cat_n"],
    "Posting cadence": ["h_gap_days", "h_posts_30d"],
}


def history_features(prior: pd.DataFrame, category: str, when: pd.Timestamp) -> dict:
    """`prior` must contain only same-platform posts published before `when`."""
    if prior.empty:
        return {k: np.nan for k in HISTORY} | {"h_cat_n": 0}
    lv = np.log1p(prior["views"].to_numpy(float))
    er = prior["engagement_rate"].to_numpy(float)
    cat = prior[prior["category"] == category]
    recent_30 = prior[prior["published_at"] >= when - pd.Timedelta(days=30)]
    return dict(
        h_logviews_10=float(lv[-10:].mean()), h_er_10=float(er[-10:].mean()),
        h_er_trend=float(er[-5:].mean() - er[-20:].mean()) if len(er) >= 6 else 0.0,
        h_cat_er=float(cat["engagement_rate"].mean()) if len(cat) else np.nan,
        h_cat_logviews=float(np.log1p(cat["views"]).mean()) if len(cat) else np.nan,
        h_cat_n=int(len(cat)),
        h_gap_days=float((when - prior["published_at"].iloc[-1]).total_seconds() / 86400),
        h_posts_30d=int(len(recent_30)))


def followers_at(ws, platform: str, when: pd.Timestamp) -> float:
    fl = ws.followers
    if not fl.empty:
        s = fl[fl["platform"] == platform].sort_values("date")
        if len(s):
            idx = s["date"].searchsorted(when.normalize(), side="right") - 1
            return float(s["followers"].iloc[max(0, min(idx, len(s) - 1))])
    return float(ws.accounts.get(platform, {}).get("followers") or 1000)


def creator_features(all_prior: pd.DataFrame, platform_prior: pd.DataFrame) -> dict:
    """Creator-wide recent momentum across ALL platforms (posts strictly before the target post).
    c_er_ratio compares the last 12 posts' engagement with the preceding 60: a drop shows up here first."""
    if len(all_prior) < 20:
        return dict(c_er_10=np.nan, c_er_ratio=1.0, c_logviews_ratio=1.0)
    er = all_prior["engagement_rate"].to_numpy(float)
    lv = np.log1p(all_prior["views"].to_numpy(float))
    base_er, base_lv = er[-72:-12], lv[-72:-12]
    if len(base_er) < 5:
        base_er, base_lv = er[:-12], lv[:-12]
    return dict(c_er_10=float(er[-12:].mean()), c_er_ratio=float(er[-12:].mean() / max(1e-9, base_er.mean())),
                c_logviews_ratio=float(lv[-12:].mean() / max(1e-9, base_lv.mean())))


def _static(row: dict) -> dict:
    tf = title_features(row.get("title", ""))
    dur = row.get("duration_sec")
    has = dur is not None and not pd.isna(dur)
    return dict(hour=int(row["hour"]), dow=int(row["dow"]), is_weekend=int(row["dow"] >= 5),
                duration_sec=float(dur) if has else 0.0, has_duration=int(has), **tf)


def build_training_frame(ws) -> pd.DataFrame:
    """One row per post with static + history features. Sorted by time."""
    df = ws.content.sort_values("published_at").reset_index(drop=True)
    rows = []
    times = df["published_at"].dt.tz_convert("UTC").dt.tz_localize(None).to_numpy()
    for p, sub in df.groupby("platform"):
        sub = sub.sort_values("published_at").reset_index(drop=True)
        for i, r in sub.iterrows():
            prior = sub.iloc[:i]
            prior = prior[prior["published_at"] < r["published_at"]]
            all_prior = df.iloc[:int(np.searchsorted(times, r["published_at"].tz_convert("UTC").tz_localize(None).to_datetime64(), side="left"))]
            feats = _static(r.to_dict()) | history_features(prior, r["category"], r["published_at"]) | creator_features(all_prior, prior)
            feats["followers_log"] = float(np.log1p(followers_at(ws, p, r["published_at"])))
            rows.append(dict(platform=p, content_type=r["content_type"], category=r["category"], published_at=r["published_at"],
                             content_id=r["content_id"], views=r["views"], engagement_rate=r["engagement_rate"], **feats))
    return pd.DataFrame(rows).sort_values("published_at").reset_index(drop=True)


def design_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    """Numeric + one-hot with a FIXED column set so training and inference always align."""
    X = frame[NUMERIC].copy()
    for p in PLATFORMS:
        X[f"platform_{p}"] = (frame["platform"] == p).astype(int)
    for t in ALL_TYPES:
        X[f"type_{t}"] = (frame["content_type"] == t).astype(int)
    for c in ALL_CATEGORIES:
        X[f"cat_{c}"] = (frame["category"] == c).astype(int)
    return X


def fit_reference(frame: pd.DataFrame) -> dict:
    """Per-platform sorted training distributions used to turn (views, engagement rate) into a 0-100 score."""
    ref = {}
    for p, sub in frame.groupby("platform"):
        ref[p] = dict(views=np.sort(sub["views"].to_numpy(float)), er=np.sort(sub["engagement_rate"].to_numpy(float)))
    return ref


def target_score(frame: pd.DataFrame, ref: dict) -> np.ndarray:
    out = np.zeros(len(frame))
    for p in frame["platform"].unique():
        m = (frame["platform"] == p).to_numpy()
        r = ref.get(p)
        if r is None:
            out[m] = 50.0
            continue
        pv = np.searchsorted(r["views"], frame.loc[m, "views"].to_numpy(float), side="right") / len(r["views"])
        pe = np.searchsorted(r["er"], frame.loc[m, "engagement_rate"].to_numpy(float), side="right") / len(r["er"])
        out[m] = 100 * (0.5 * pv + 0.5 * pe)
    return out
