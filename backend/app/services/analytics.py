"""Analytics engine: answers "what happened?" over the unified Content layer.

Every function takes a Workspace (+ optional Filters) and returns plain JSON-safe dicts. No platform
specifics live here. Anything that cannot be computed from the data returns None / an explicit note.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.schemas.content import PLATFORM_LABELS
from app.services.dataset import Workspace

_MEMO: dict = {}


def memo(fn):
    """Cache heavy, deterministic analytics per (workspace key, args). Workspace keys change when data changes."""
    import functools

    @functools.wraps(fn)
    def wrapper(ws, f=None, *a, **kw):
        key = (fn.__name__, ws.key, repr(f), a, tuple(sorted(kw.items())))
        if key not in _MEMO:
            if len(_MEMO) > 400:
                _MEMO.clear()
            _MEMO[key] = fn(ws, f, *a, **kw)
        return _MEMO[key]
    return wrapper




DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


@dataclass
class Filters:
    days: int | None = None
    platforms: list[str] | None = None
    category: str | None = None
    content_type: str | None = None
    start: date | None = None
    end: date | None = None


def clean(o):
    """Make numpy / pandas objects JSON-safe (NaN -> None)."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(o, (pd.Timestamp, datetime, date)):
        return o.isoformat()
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def with_perf(df: pd.DataFrame) -> pd.DataFrame:
    """Descriptive performance index (0-100): within-platform percentile of views and engagement rate."""
    df = df.copy()
    if df.empty:
        df["perf_index"] = []
        return df
    pv = df.groupby("platform")["views"].rank(pct=True)
    pe = df.groupby("platform")["engagement_rate"].rank(pct=True)
    df["perf_index"] = (100 * (0.5 * pv + 0.5 * pe)).round(1)
    return df


def anchor(ws: Workspace) -> pd.Timestamp:
    return ws.content["published_at"].max() if len(ws.content) else pd.Timestamp.now(tz="UTC")


def apply_filters(ws: Workspace, f: Filters | None) -> pd.DataFrame:
    df = with_perf(ws.content)
    if f is None or df.empty:
        return df
    if f.platforms:
        df = df[df["platform"].isin(f.platforms)]
    if f.category:
        df = df[df["category"] == f.category]
    if f.content_type:
        df = df[df["content_type"] == f.content_type]
    end = anchor(ws)
    if f.days:
        df = df[df["published_at"] >= end - pd.Timedelta(days=f.days)]
    if f.start:
        df = df[df["published_at"].dt.date >= f.start]
    if f.end:
        df = df[df["published_at"].dt.date <= f.end]
    return df


def _agg(df: pd.DataFrame) -> dict:
    if df.empty:
        return dict(posts=0, views=0, interactions=0, likes=0, comments=0, shares=0, engagement_rate=None, avg_views=None)
    views, inter = int(df["views"].sum()), int(df["interactions"].sum())
    return dict(posts=int(len(df)), views=views, interactions=inter, likes=int(df["likes"].sum()),
                comments=int(df["comments"].sum()), shares=int(df["shares"].sum()),
                engagement_rate=inter / views if views else None, avg_views=float(df["views"].mean()))


def _pct(new, old):
    if new is None or old in (None, 0):
        return None
    return (new - old) / old * 100


def follower_change(ws: Workspace, days: int, platforms: list[str] | None = None) -> dict:
    """Follower growth over the trailing window, from stored history. None when history is unavailable."""
    fl = ws.followers
    if fl.empty:
        return dict(available=False, start=None, end=None, change=None, pct=None)
    if platforms:
        fl = fl[fl["platform"].isin(platforms)]
    tot = fl.groupby("date")["followers"].sum().sort_index()
    if len(tot) < 2:
        return dict(available=False, start=None, end=None, change=None, pct=None)
    end_v = float(tot.iloc[-1])
    cutoff = tot.index[-1] - pd.Timedelta(days=days)
    start_v = float(tot[tot.index <= cutoff].iloc[-1]) if (tot.index <= cutoff).any() else float(tot.iloc[0])
    return dict(available=True, start=start_v, end=end_v, change=end_v - start_v,
                pct=(end_v - start_v) / start_v * 100 if start_v else None)


def summary(ws: Workspace, f: Filters | None = None) -> dict:
    f = f or Filters(days=30)
    days = f.days or 30
    df_all = apply_filters(ws, Filters(platforms=f.platforms, category=f.category, content_type=f.content_type))
    end = anchor(ws)
    cur = df_all[df_all["published_at"] > end - pd.Timedelta(days=days)]
    prev = df_all[(df_all["published_at"] <= end - pd.Timedelta(days=days)) &
                  (df_all["published_at"] > end - pd.Timedelta(days=2 * days))]
    a, b = _agg(cur), _agg(prev)
    fc = follower_change(ws, days, f.platforms)
    followers_now = sum(v["followers"] for p, v in ws.accounts.items() if not f.platforms or p in f.platforms)
    return clean(dict(
        window_days=days, source=ws.source.model_dump(), current=a, previous=b,
        deltas=dict(views_pct=_pct(a["views"], b["views"]), interactions_pct=_pct(a["interactions"], b["interactions"]),
                    engagement_rate_pct=_pct(a["engagement_rate"], b["engagement_rate"]), posts_pct=_pct(a["posts"], b["posts"])),
        followers=dict(total=followers_now, **fc),
        platforms_included=sorted(df_all["platform"].unique().tolist()) if len(df_all) else [],
        as_of=end.isoformat() if len(ws.content) else None))


def timeseries(ws: Workspace, f: Filters | None = None, freq: str = "W") -> dict:
    df = apply_filters(ws, f)
    if df.empty:
        return dict(freq=freq, points=[], followers=[])
    rule = {"D": "D", "W": "W-MON", "M": "MS"}.get(freq, "W-MON")
    g = df.set_index("published_at")
    out = []
    for p, sub in g.groupby("platform"):
        r = sub.resample(rule).agg(views=("views", "sum"), interactions=("interactions", "sum"), posts=("views", "count"))
        r["engagement_rate"] = r["interactions"] / r["views"].replace(0, np.nan)
        for ts, row in r.iterrows():
            out.append(dict(date=ts, platform=p, views=row["views"], interactions=row["interactions"],
                            posts=row["posts"], engagement_rate=row["engagement_rate"]))
    tot = pd.DataFrame(out).groupby("date").agg(views=("views", "sum"), interactions=("interactions", "sum"), posts=("posts", "sum")).reset_index()
    tot["engagement_rate"] = tot["interactions"] / tot["views"].replace(0, np.nan)
    fol = []
    if not ws.followers.empty:
        fl = ws.followers
        if f and f.platforms:
            fl = fl[fl["platform"].isin(f.platforms)]
        t = fl.groupby("date")["followers"].sum().reset_index()
        t = t.iloc[:: {"D": 1, "W": 7, "M": 30}.get(freq, 7)]
        fol = t.to_dict("records")
    return clean(dict(freq=freq, points=tot.to_dict("records"), by_platform=out, followers=fol))


def platform_comparison(ws: Workspace, f: Filters | None = None) -> dict:
    df = apply_filters(ws, f)
    days = (f.days if f and f.days else 30)
    rows = []
    for p in ws.platforms:
        sub = df[df["platform"] == p]
        if sub.empty:
            continue
        a = _agg(sub)
        followers = ws.accounts.get(p, {}).get("followers")
        fc = follower_change(ws, days, [p])
        rows.append(dict(
            platform=p, label=PLATFORM_LABELS[p], **a, followers=followers, follower_growth_pct=fc["pct"],
            views_per_follower=(a["avg_views"] / followers) if followers else None,
            interactions_per_1k_followers=(sub["interactions"].mean() / followers * 1000) if followers else None,
            median_engagement_rate=float(sub["engagement_rate"].median()), avg_perf_index=float(sub["perf_index"].mean())))
    best = {}
    for key in ("engagement_rate", "views_per_follower", "follower_growth_pct", "views"):
        c = [r for r in rows if r.get(key) is not None]
        best[key] = max(c, key=lambda r: r[key])["platform"] if c else None
    return clean(dict(platforms=rows, best=best, window_days=f.days if f else None,
                      note="Engagement rate = (likes + comments + shares) / views. Platforms define views differently, so compare "
                           "rates and per-follower figures rather than raw view counts."))


def _content_row(r: pd.Series) -> dict:
    return dict(platform=r["platform"], content_id=r["content_id"], title=r["title"], content_type=r["content_type"],
                category=r["category"], published_at=r["published_at"], views=int(r["views"]), likes=int(r["likes"]),
                comments=int(r["comments"]), shares=int(r["shares"]), engagement_rate=float(r["engagement_rate"]),
                perf_index=float(r["perf_index"]))


def top_content(ws: Workspace, f: Filters | None = None, n: int = 5, worst: bool = False) -> dict:
    df = apply_filters(ws, f)
    if df.empty:
        return dict(items=[], worst=worst)
    df = df.sort_values("perf_index", ascending=worst).head(n)
    return clean(dict(items=[_content_row(r) for _, r in df.iterrows()], worst=worst,
                      note="Ranked by performance index: within-platform percentile of views and engagement rate."))


def content_list(ws: Workspace, f: Filters | None = None, sort: str = "published_at", limit: int = 100, search: str | None = None) -> dict:
    df = apply_filters(ws, f)
    if search:
        df = df[df["title"].str.contains(search, case=False, na=False, regex=False)]
    if sort in df.columns:
        df = df.sort_values(sort, ascending=False)
    return clean(dict(total=int(len(df)), items=[_content_row(r) for _, r in df.head(limit).iterrows()]))


def content_details(ws: Workspace, content_id: str) -> dict | None:
    df = with_perf(ws.content)
    m = df[df["content_id"] == content_id]
    if m.empty:
        return None
    r = m.iloc[0]
    peers = df[df["platform"] == r["platform"]]
    d = _content_row(r)
    d["duration_sec"] = None if pd.isna(r["duration_sec"]) else int(r["duration_sec"])
    d["vs_platform_median"] = dict(
        views_ratio=float(r["views"] / max(1.0, peers["views"].median())),
        engagement_rate_ratio=float(r["engagement_rate"] / max(1e-9, peers["engagement_rate"].median())))
    d["publish_slot"] = f"{DOW[int(r['dow'])]} {int(r['hour']):02d}:00 UTC"
    return clean(d)


@memo
def best_publish_times(ws: Workspace, f: Filters | None = None, min_n: int = 3) -> dict:
    """Shrunk means (toward the platform average) so thin slots do not look better than they are."""
    df = apply_filters(ws, f)
    out = {}
    K = 4.0
    for p in ws.platforms:
        sub = df[df["platform"] == p]
        if len(sub) < 12:
            continue
        mu = sub["perf_index"].mean()
        def shrink(g):
            n = len(g)
            return pd.Series(dict(n=n, score=(g["perf_index"].sum() + K * mu) / (n + K), raw=g["perf_index"].mean()))
        hrs = sub.groupby("hour").apply(shrink, include_groups=False).reset_index()
        days = sub.groupby("dow").apply(shrink, include_groups=False).reset_index()
        hrs, days = hrs[hrs["n"] >= min_n], days[days["n"] >= min_n]
        heat = sub.assign(block=sub["hour"] // 3 * 3).groupby(["dow", "block"])["perf_index"].agg(["mean", "count"]).reset_index()
        out[p] = dict(
            best_hours=[dict(hour=int(r["hour"]), score=float(r["score"]), n=int(r["n"])) for _, r in hrs.sort_values("score", ascending=False).head(3).iterrows()],
            best_days=[dict(day=DOW[int(r["dow"])], score=float(r["score"]), n=int(r["n"])) for _, r in days.sort_values("score", ascending=False).head(3).iterrows()],
            heatmap=[dict(day=DOW[int(r["dow"])], dow=int(r["dow"]), block=int(r["block"]), score=float(r["mean"]), n=int(r["count"])) for _, r in heat.iterrows()],
            baseline=float(mu), posts=int(len(sub)))
    return clean(dict(by_platform=out, timezone="UTC",
                      note=f"Slots need at least {min_n} posts and are shrunk toward each platform's average to avoid small-sample noise."))


def analyze_categories(ws: Workspace, f: Filters | None = None) -> dict:
    df = apply_filters(ws, f)
    if df.empty:
        return dict(categories=[], by_platform=[], formats=[])
    def block(by):
        g = df.groupby(by).agg(posts=("views", "count"), avg_views=("views", "mean"), engagement_rate=("engagement_rate", "median"),
                               perf_index=("perf_index", "mean")).reset_index()
        return g.sort_values("perf_index", ascending=False)
    return clean(dict(categories=block("category").to_dict("records"),
                      by_platform=block(["platform", "category"]).to_dict("records"),
                      formats=block(["platform", "content_type"]).to_dict("records")))


def engagement_breakdown(ws: Workspace, f: Filters | None = None) -> dict:
    df = apply_filters(ws, f)
    rows = []
    for p in ws.platforms:
        s = df[df["platform"] == p]
        if s.empty:
            continue
        t = max(1, int(s["interactions"].sum()))
        rows.append(dict(platform=p, label=PLATFORM_LABELS[p], likes=int(s["likes"].sum()), comments=int(s["comments"].sum()),
                         shares=int(s["shares"].sum()), likes_pct=s["likes"].sum() / t, comments_pct=s["comments"].sum() / t,
                         shares_pct=s["shares"].sum() / t))
    return clean(dict(platforms=rows))


def compare_periods(ws: Workspace, days: int = 28, platforms: list[str] | None = None) -> dict:
    df = apply_filters(ws, Filters(platforms=platforms))
    end = anchor(ws)
    cur = df[df["published_at"] > end - pd.Timedelta(days=days)]
    prev = df[(df["published_at"] <= end - pd.Timedelta(days=days)) & (df["published_at"] > end - pd.Timedelta(days=2 * days))]
    a, b = _agg(cur), _agg(prev)
    per = {}
    for p in sorted(df["platform"].unique()) if len(df) else []:
        pa, pb = _agg(cur[cur["platform"] == p]), _agg(prev[prev["platform"] == p])
        per[p] = dict(current=pa, previous=pb, engagement_rate_pct=_pct(pa["engagement_rate"], pb["engagement_rate"]),
                      views_pct=_pct(pa["views"], pb["views"]))
    return clean(dict(days=days, current=a, previous=b, engagement_rate_pct=_pct(a["engagement_rate"], b["engagement_rate"]),
                      views_pct=_pct(a["views"], b["views"]), by_platform=per))


def explain_engagement_change(ws: Workspace, days: int = 28, platforms: list[str] | None = None) -> dict:
    """Decompose the change in blended engagement rate into rate effects and mix effects, per platform
    and per category, with a significance test on post-level rates. Midpoint decomposition: sums exactly to the change."""
    df = apply_filters(ws, Filters(platforms=platforms))
    end = anchor(ws)
    cur = df[df["published_at"] > end - pd.Timedelta(days=days)]
    prev = df[(df["published_at"] <= end - pd.Timedelta(days=days)) & (df["published_at"] > end - pd.Timedelta(days=2 * days))]
    if len(cur) < 5 or len(prev) < 5:
        return dict(available=False, reason="Not enough posts in both periods to compare.")
    r1, r0 = cur["interactions"].sum() / cur["views"].sum(), prev["interactions"].sum() / prev["views"].sum()

    def decompose(col):
        keys = sorted(set(cur[col]) | set(prev[col]))
        rows = []
        for k in keys:
            c, p = cur[cur[col] == k], prev[prev[col] == k]
            w1, w0 = c["views"].sum() / cur["views"].sum(), p["views"].sum() / prev["views"].sum()
            rr1 = c["interactions"].sum() / c["views"].sum() if len(c) else None
            rr0 = p["interactions"].sum() / p["views"].sum() if len(p) else None
            if rr1 is None or rr0 is None:
                rate_eff = 0.0
                mix_eff = (w1 * (rr1 if rr1 is not None else r1)) - (w0 * (rr0 if rr0 is not None else r0))
            else:
                rate_eff = (w0 + w1) / 2 * (rr1 - rr0)
                mix_eff = (rr0 + rr1) / 2 * (w1 - w0)
            rows.append(dict(key=k, effect=rate_eff + mix_eff, rate_effect=rate_eff, mix_effect=mix_eff,
                             rate_now=rr1, rate_before=rr0, view_share_now=w1, view_share_before=w0,
                             posts_now=int(len(c)), posts_before=int(len(p))))
        return sorted(rows, key=lambda x: x["effect"])

    cm_now = cur["comments"].sum() / max(1, cur["interactions"].sum())
    cm_prev = prev["comments"].sum() / max(1, prev["interactions"].sum())
    try:
        p_val = float(mannwhitneyu(cur["engagement_rate"], prev["engagement_rate"], alternative="two-sided").pvalue)
    except ValueError:
        p_val = None
    by_platform, by_category = decompose("platform"), decompose("category")
    drivers = [dict(dimension="platform", **r) for r in by_platform] + [dict(dimension="category", **r) for r in by_category]
    drivers = sorted(drivers, key=lambda x: x["effect"])
    return clean(dict(
        available=True, days=days, rate_now=r1, rate_before=r0, change_pct=_pct(r1, r0), change_abs=r1 - r0,
        significant=(p_val is not None and p_val < 0.05), p_value=p_val,
        comment_share_now=cm_now, comment_share_before=cm_prev,
        by_platform=by_platform, by_category=by_category, top_negative=drivers[:3], top_positive=drivers[::-1][:3],
        posts_now=int(len(cur)), posts_before=int(len(prev)),
        method="Change in blended engagement rate split into per-segment rate effects and audience-mix effects (midpoint decomposition). "
               "Significance: Mann-Whitney U on post-level engagement rates."))


@memo
def detect_anomalies(ws: Workspace, f: Filters | None = None, z_thresh: float = 3.5, recent_days: int = 90) -> dict:
    """Robust (median/MAD) z-scores of each post's views and engagement rate against the platform's PRIOR posts,
    plus daily follower-growth outliers. Statistical thresholds, not a black box."""
    df = apply_filters(ws, Filters(platforms=f.platforms if f else None))
    end = anchor(ws)
    found = []
    for p, sub in df.groupby("platform"):
        sub = sub.sort_values("published_at").reset_index(drop=True)
        lv, er = np.log1p(sub["views"].to_numpy(float)), sub["engagement_rate"].to_numpy(float)
        cr = (sub["comments"] / sub["views"].clip(lower=1)).to_numpy(float)
        for i in range(15, len(sub)):
            if sub.loc[i, "published_at"] < end - pd.Timedelta(days=recent_days):
                continue
            for name, arr, label in (("views", lv, "Views"), ("engagement_rate", er, "Engagement rate"), ("comment_rate", cr, "Comment activity")):
                hist = arr[max(0, i - 60):i]
                med = np.median(hist)
                mad = np.median(np.abs(hist - med)) * 1.4826 or 1e-9
                z = (arr[i] - med) / mad
                if abs(z) >= z_thresh:
                    r = sub.loc[i]
                    found.append(dict(platform=p, metric=name, direction="high" if z > 0 else "low", z=float(z),
                                      content_id=r["content_id"], title=r["title"], published_at=r["published_at"],
                                      value=float(np.expm1(arr[i]) if name == "views" else arr[i]),
                                      typical=float(np.expm1(med) if name == "views" else med),
                                      message=f"{label} on {PLATFORM_LABELS[p]} is significantly {'above' if z > 0 else 'below'} your normal range."))
    if not ws.followers.empty:
        for p, sub in ws.followers.groupby("platform"):
            d = sub.sort_values("date")["followers"].diff().dropna()
            if len(d) < 30:
                continue
            for i in range(30, len(d)):
                hist = d.iloc[i - 30:i]
                med, mad = hist.median(), (hist - hist.median()).abs().median() * 1.4826 or 1e-9
                z = (d.iloc[i] - med) / mad
                dt = sub.sort_values("date")["date"].iloc[i + 1]
                if abs(z) >= z_thresh and dt >= end.normalize() - pd.Timedelta(days=recent_days):
                    found.append(dict(platform=p, metric="follower_growth", direction="high" if z > 0 else "low", z=float(z),
                                      published_at=dt, value=float(d.iloc[i]), typical=float(med), content_id=None, title=None,
                                      message=f"Daily follower growth on {PLATFORM_LABELS[p]} is outside your normal range."))
    found.sort(key=lambda x: -abs(x["z"]))
    return clean(dict(items=found[:25], count=len(found), threshold=z_thresh, window_days=recent_days,
                      method="Robust z-score (median/MAD) against each platform's previous 60 posts or 30 days."))


@memo
def cross_platform(ws: Workspace, f: Filters | None = None) -> dict:
    df = apply_filters(ws, f)
    if df.empty:
        return dict(category_fit=[], best_platform_by_category={}, same_idea=[], focus=None)
    # relative fit: category perf_index vs that platform's overall mean (so platform size cancels out)
    base = df.groupby("platform")["perf_index"].mean()
    g = df.groupby(["category", "platform"]).agg(n=("views", "count"), perf=("perf_index", "mean"), er=("engagement_rate", "median")).reset_index()
    g = g[g["n"] >= 3]
    g["lift"] = g["perf"] / g["platform"].map(base)
    best = {c: sub.sort_values("lift", ascending=False).iloc[0]["platform"] for c, sub in g.groupby("category")}
    # same-idea heuristic: TF-IDF title similarity across platforms within a 10-day window
    groups = []
    sub = df.reset_index(drop=True)
    if len(sub) > 10:
        tf = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1).fit_transform(sub["title"].fillna(""))
        sim = cosine_similarity(tf)
        used = set()
        for i in range(len(sub)):
            if i in used:
                continue
            members = [i]
            for j in range(i + 1, len(sub)):
                if j in used or sub.loc[j, "platform"] in {sub.loc[m, "platform"] for m in members}:
                    continue
                if sim[i, j] >= 0.35 and abs((sub.loc[j, "published_at"] - sub.loc[i, "published_at"]).days) <= 10:
                    members.append(j)
            if len(members) >= 2:
                used.update(members)
                posts = []
                for m in members:
                    r = sub.loc[m]
                    fol = ws.accounts.get(r["platform"], {}).get("followers")
                    posts.append(dict(platform=r["platform"], title=r["title"], views=int(r["views"]),
                                      engagement_rate=float(r["engagement_rate"]), views_per_follower=(r["views"] / fol) if fol else None))
                groups.append(dict(posts=posts, best_platform=max(posts, key=lambda x: x["engagement_rate"])["platform"]))
    plat = platform_comparison(ws, f)
    focus = None
    cand = [r for r in plat["platforms"] if r.get("interactions_per_1k_followers") is not None]
    if cand:
        focus = max(cand, key=lambda r: r["interactions_per_1k_followers"])["platform"]
    return clean(dict(
        category_fit=g.to_dict("records"), best_platform_by_category=best, same_idea=groups[:8], focus=focus,
        method_note="Same-idea groups use TF-IDF title similarity (>= 0.35) within a 10-day window: a heuristic, not semantic matching. "
                    "Category lift compares each category's performance index with that platform's own average."))


def creator_profile(ws: Workspace, f: Filters | None = None) -> dict:
    """Five data-backed dimensions, each 0-100 against fixed, documented anchors. Not a psychological profile."""
    df = apply_filters(ws, Filters(days=(f.days if f and f.days else 90), platforms=f.platforms if f else None))
    if len(df) < 8:
        return dict(available=False, reason="Not enough recent posts to build a profile.")
    dims = {}
    fc = follower_change(ws, 90, f.platforms if f else None)
    if fc["available"] and fc["pct"] is not None:
        dims["growth"] = dict(score=min(100, max(0, fc["pct"] * 8)), value=fc["pct"], unit="% follower growth, 90d",
                              formula="10% growth in 90 days = 80 points")
    er = float(df["engagement_rate"].median())
    dims["engagement"] = dict(score=min(100, er / 0.08 * 100), value=er, unit="median engagement rate", formula="8% median rate = 100")
    reach_ratio = 0.0
    parts = []
    for p, s in df.groupby("platform"):
        fol = ws.accounts.get(p, {}).get("followers")
        if fol:
            parts.append(s["views"].median() / fol)
    if parts:
        reach_ratio = float(np.mean(parts))
        dims["reach"] = dict(score=min(100, reach_ratio / 0.5 * 100), value=reach_ratio, unit="median views per follower", formula="0.5 views per follower = 100")
    weekly = df.set_index("published_at").resample("W-MON").size()
    if len(weekly) >= 4:
        cv = float(weekly.std() / weekly.mean()) if weekly.mean() else 1.0
        dims["consistency"] = dict(score=max(0, min(100, (1 - cv) * 100)), value=cv, unit="weekly posting variability (CV)", formula="score = (1 - CV) x 100")
    cr = float((df["comments"].sum() / max(1, df["views"].sum())) * 1000)
    dims["community"] = dict(score=min(100, cr / 8 * 100), value=cr, unit="comments per 1,000 views", formula="8 per 1,000 = 100")
    ranked = sorted(dims.items(), key=lambda kv: -kv[1]["score"])
    strengths, focus = [k for k, _ in ranked[:2]], ranked[-1][0]
    return clean(dict(available=True, dimensions=dims, strengths=strengths, focus_area=focus, posts_analyzed=int(len(df)),
                      summary=f"Strongest on {strengths[0]} and {strengths[1]}; most room to improve in {focus}.",
                      note="Scores compare your own metrics with fixed anchors shown in each formula. They describe performance, not personality."))


def _insights(ws: Workspace, f=None) -> dict:
    """Headline + explained-why cards, every one backed by numbers from the functions above."""
    cards = []
    s = summary(ws, Filters(days=30))
    fol = s["followers"]
    if fol.get("available") and fol.get("pct") is not None:
        pc = platform_comparison(ws, Filters(days=30))["platforms"]
        gr = sorted([r for r in pc if r.get("follower_growth_pct") is not None], key=lambda r: -r["follower_growth_pct"])
        why = f"{gr[0]['label']} grew fastest (+{gr[0]['follower_growth_pct']:.1f}%)." if gr else ""
        cards.append(dict(kind="growth", tone="positive" if fol["pct"] >= 0 else "negative",
                          headline=f"Your audience {'grew' if fol['pct'] >= 0 else 'shrank'} {abs(fol['pct']):.1f}% in the last 30 days.",
                          why=why, evidence=dict(followers_change=fol["change"], pct=fol["pct"])))
    ex = explain_engagement_change(ws, 28)
    if ex.get("available") and ex["change_pct"] is not None and abs(ex["change_pct"]) >= 3:
        drv = ex["top_negative"][0] if ex["change_pct"] < 0 else ex["top_positive"][0]
        cards.append(dict(kind="engagement", tone="negative" if ex["change_pct"] < 0 else "positive",
                          headline=f"Engagement {'fell' if ex['change_pct'] < 0 else 'rose'} {abs(ex['change_pct']):.1f}% vs the previous 28 days.",
                          why=f"Biggest driver: {PLATFORM_LABELS.get(drv['key'], drv['key'])} ({drv['dimension']}) at {drv['effect'] * 100:+.2f} pts. "
                              f"{'Statistically significant.' if ex['significant'] else 'Not statistically significant: could be normal variation.'}",
                          evidence=dict(rate_now=ex["rate_now"], rate_before=ex["rate_before"], p_value=ex["p_value"])))
    bt = best_publish_times(ws)["by_platform"]
    if bt:
        p, v = max(bt.items(), key=lambda kv: kv[1]["best_hours"][0]["score"] / kv[1]["baseline"] if kv[1]["best_hours"] else 0)
        if v["best_hours"] and v["best_days"]:
            cards.append(dict(kind="timing", tone="neutral", headline=f"Best {PLATFORM_LABELS[p]} slot: {v['best_days'][0]['day']} around {v['best_hours'][0]['hour']:02d}:00 UTC.",
                              why=f"Posts in this window score {v['best_hours'][0]['score'] - v['baseline']:+.0f} points vs your {PLATFORM_LABELS[p]} average.",
                              evidence=v["best_hours"][0]))
    an = detect_anomalies(ws, None, recent_days=60)
    if an["items"]:
        a = an["items"][0]
        cards.append(dict(kind="anomaly", tone="attention", headline=a["message"], why=(a.get("title") or "")[:120], evidence=dict(z=a["z"], value=a["value"], typical=a["typical"])))
    cp = cross_platform(ws)
    if cp.get("focus"):
        cards.append(dict(kind="focus", tone="neutral", headline=f"{PLATFORM_LABELS[cp['focus']]} gives you the most engagement per follower.",
                          why="Interactions per 1,000 followers, per post, is highest there.", evidence=dict(platform=cp["focus"])))
    return clean(dict(cards=cards, source=ws.source.model_dump()))


insights = memo(_insights)
