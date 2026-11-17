"""The Digital Assistant's tool layer. Every tool wraps real analytics/ML code and returns structured data.

Each result is {"data": <what the LLM may see>, "card": <what the UI renders>}.
Privacy: results contain metrics, categories and (truncated) post titles only. No account handles, emails or tokens
ever leave the server toward an LLM provider.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from app.ml import pipeline as ml
from app.schemas.content import CATEGORIES, CONTENT_TYPES, PLATFORM_LABELS, PLATFORMS
from app.services import analytics as A
from app.services.dataset import Workspace


def _f(days=None, platform=None, category=None) -> A.Filters:
    return A.Filters(days=days, platforms=[platform] if platform else None, category=category)


def _short(items: list[dict], n=80) -> list[dict]:
    for i in items:
        if i.get("title"):
            i["title"] = i["title"][:n]
    return items


# ---------------------------------------------------------------- tools
def get_channel_summary(ws, days: int = 30, platform: str | None = None):
    s = A.summary(ws, _f(days, platform))
    s.pop("source", None)
    return dict(data=s, card=dict(type="summary", **s))


def get_platform_metrics(ws, platform: str, days: int = 30):
    pc = A.platform_comparison(ws, _f(days))
    row = next((r for r in pc["platforms"] if r["platform"] == platform), None)
    if not row:
        return dict(data=dict(error=f"No {PLATFORM_LABELS.get(platform, platform)} data available."), card=None)
    return dict(data=row, card=dict(type="platform_comparison", platforms=[row], best=pc["best"], note=pc["note"]))


def get_top_content(ws, n: int = 5, platform: str | None = None, worst: bool = False, days: int | None = None):
    t = A.top_content(ws, _f(days, platform), n=min(max(n, 1), 10), worst=worst)
    t["items"] = _short(t["items"])
    return dict(data=t, card=dict(type="top_content", **t))


def get_content_details(ws, content_id: str):
    d = A.content_details(ws, content_id)
    return dict(data=d or dict(error="No content with that id."), card=None)


def compare_platforms(ws, days: int = 30):
    pc = A.platform_comparison(ws, _f(days))
    cp = A.cross_platform(ws, _f(days))
    data = dict(**pc, focus_by_engagement_per_follower=cp.get("focus"), best_platform_by_category=cp.get("best_platform_by_category"))
    return dict(data=data, card=dict(type="platform_comparison", platforms=pc["platforms"], best=pc["best"], note=pc["note"],
                                     focus=cp.get("focus")))


def compare_periods(ws, days: int = 28, platform: str | None = None):
    r = A.compare_periods(ws, days, [platform] if platform else None)
    return dict(data=r, card=dict(type="period_compare", **r))


def analyze_engagement(ws, days: int = 28, platform: str | None = None):
    r = A.explain_engagement_change(ws, days, [platform] if platform else None)
    card = dict(type="engagement_change", **r) if r.get("available") else None
    return dict(data=r, card=card)


def find_best_publish_time(ws, platform: str | None = None):
    r = A.best_publish_times(ws, _f(None, platform))
    return dict(data=r, card=dict(type="best_times", **r))


def analyze_categories(ws, platform: str | None = None):
    r = A.analyze_categories(ws, _f(None, platform))
    return dict(data=dict(categories=r["categories"], by_platform=r["by_platform"]), card=dict(type="categories", **r))


def detect_anomalies(ws, platform: str | None = None, days: int = 90):
    r = A.detect_anomalies(ws, _f(None, platform), recent_days=days)
    r["items"] = _short(r["items"])
    return dict(data=r, card=dict(type="anomalies", **r))


def predict_content_performance(ws, title: str, platform: str, category: str, content_type: str | None = None,
                                duration_sec: int | None = None, publish_at: str | None = None):
    if platform not in PLATFORMS:
        return dict(data=dict(error="Unknown platform."), card=None)
    ct = content_type if content_type in CONTENT_TYPES[platform] else CONTENT_TYPES[platform][0]
    when = publish_at or (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0).isoformat()
    try:
        r = ml.predict(ws, dict(title=title or "", platform=platform, category=category if category in CATEGORIES else "General",
                                content_type=ct, duration_sec=duration_sec, publish_at=when))
    except ValueError as e:
        return dict(data=dict(error=str(e)), card=None)
    return dict(data=r, card=dict(type="prediction", **r))


def get_creator_profile(ws):
    r = A.creator_profile(ws)
    return dict(data=r, card=dict(type="profile", **r) if r.get("available") else None)


def generate_content_strategy(ws):
    """Combines analytics + ML. Every recommendation carries the evidence it came from."""
    recs, evidence = [], {}
    cp = A.cross_platform(ws)
    pc = A.platform_comparison(ws, A.Filters(days=90))
    evidence["platform_best"] = pc["best"]
    if cp.get("focus"):
        recs.append(dict(kind="focus", text=f"Prioritise {PLATFORM_LABELS[cp['focus']]}: highest engagement per follower.", platform=cp["focus"]))
    bt = A.best_publish_times(ws)["by_platform"]
    for p, v in bt.items():
        if v["best_hours"] and v["best_days"]:
            recs.append(dict(kind="timing", platform=p, text=f"{PLATFORM_LABELS[p]}: post {v['best_days'][0]['day']} near {v['best_hours'][0]['hour']:02d}:00 UTC."))
    cats = A.analyze_categories(ws)["categories"]
    if cats:
        recs.append(dict(kind="category", text=f"Strongest topic type overall: {cats[0]['category']} (performance index {cats[0]['perf_index']:.0f}).",
                         category=cats[0]["category"]))
    ideas = []
    try:
        ideas = ml.best_ideas(ws, top=4)
        for i in ideas[:3]:
            recs.append(dict(kind="idea", platform=i["platform"],
                             text=f"Model-predicted strong slot: a {i['category']} {i['content_type']} on {PLATFORM_LABELS[i['platform']]}, {i['day']} ~{i['hour']:02d}:00 UTC (score {i['score']:.0f}/100)."))
    except ValueError as e:
        evidence["ml_unavailable"] = str(e)
    ex = A.explain_engagement_change(ws, 28)
    caution = None
    if ex.get("available") and ex["change_pct"] is not None and ex["change_pct"] < -5:
        d = ex["top_negative"][0]
        caution = f"Engagement is down {abs(ex['change_pct']):.0f}% vs the prior 28 days; weakest segment: {PLATFORM_LABELS.get(d['key'], d['key'])}."
    data = dict(recommendations=recs, ideas=ideas, caution=caution, evidence=evidence)
    return dict(data=data, card=dict(type="strategy", **data))


TOOLS = {f.__name__: f for f in (get_channel_summary, get_platform_metrics, get_top_content, get_content_details, compare_platforms,
                                 compare_periods, analyze_engagement, find_best_publish_time, analyze_categories, detect_anomalies,
                                 predict_content_performance, get_creator_profile, generate_content_strategy)}

_PLAT = {"type": "string", "enum": PLATFORMS}
TOOL_SCHEMAS = [
    dict(name="get_channel_summary", description="Totals for views, interactions, engagement rate, posts and follower growth over the last N days, with change vs the previous N days.",
         input_schema=dict(type="object", properties=dict(days=dict(type="integer", minimum=7, maximum=180), platform=_PLAT))),
    dict(name="get_platform_metrics", description="Detailed metrics for one platform.",
         input_schema=dict(type="object", properties=dict(platform=_PLAT, days=dict(type="integer")), required=["platform"])),
    dict(name="get_top_content", description="Best (or worst, if worst=true) posts by performance index.",
         input_schema=dict(type="object", properties=dict(n=dict(type="integer"), platform=_PLAT, worst=dict(type="boolean"), days=dict(type="integer")))),
    dict(name="get_content_details", description="Metrics for one post by content_id.",
         input_schema=dict(type="object", properties=dict(content_id=dict(type="string")), required=["content_id"])),
    dict(name="compare_platforms", description="Compare all connected platforms: engagement rate, views per follower, follower growth, which platform to focus on.",
         input_schema=dict(type="object", properties=dict(days=dict(type="integer")))),
    dict(name="compare_periods", description="Compare the last N days with the N days before.",
         input_schema=dict(type="object", properties=dict(days=dict(type="integer"), platform=_PLAT))),
    dict(name="analyze_engagement", description="Explain WHY blended engagement changed: decomposes the change by platform and category and tests significance. Use for 'why did engagement drop/rise'.",
         input_schema=dict(type="object", properties=dict(days=dict(type="integer"), platform=_PLAT))),
    dict(name="find_best_publish_time", description="Best publishing hours and weekdays per platform (UTC).",
         input_schema=dict(type="object", properties=dict(platform=_PLAT))),
    dict(name="analyze_categories", description="Performance by topic category and content format.",
         input_schema=dict(type="object", properties=dict(platform=_PLAT))),
    dict(name="detect_anomalies", description="Unusual views, engagement, comment activity or follower growth.",
         input_schema=dict(type="object", properties=dict(platform=_PLAT, days=dict(type="integer")))),
    dict(name="predict_content_performance", description="Predict the 0-100 performance score for a planned post with SHAP explanation, uncertainty interval and what-if recommendations.",
         input_schema=dict(type="object", properties=dict(title=dict(type="string"), platform=_PLAT, category=dict(type="string", enum=CATEGORIES),
                                                          content_type=dict(type="string"), duration_sec=dict(type="integer"), publish_at=dict(type="string", description="ISO datetime, UTC")),
                           required=["platform", "category"])),
    dict(name="get_creator_profile", description="Creator profile / Social DNA: growth, engagement, reach, consistency, community scores.",
         input_schema=dict(type="object", properties={})),
    dict(name="generate_content_strategy", description="What to post next: combines platform comparison, publish-time patterns, category performance and ML predictions.",
         input_schema=dict(type="object", properties={})),
]


def run_tool(ws: Workspace, name: str, args: dict) -> dict:
    fn = TOOLS.get(name)
    if fn is None:
        return dict(data=dict(error=f"Unknown tool {name}"), card=None)
    try:
        return fn(ws, **{k: v for k, v in (args or {}).items() if v is not None})
    except TypeError as e:
        return dict(data=dict(error=f"Bad arguments: {e}"), card=None)
