"""Deterministic DEMO DATA for a fictional creator ("Nova Chen", tech educator).

Everything here is synthetic. It is generated from a fixed seed with realistic structure
(platform baselines, category/hour/day effects, an engagement dip in the most recent weeks, a
viral outlier, steady follower growth). It is only ever served to demo sessions and is always
labelled DEMO DATA in the API and UI.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from app.schemas.content import CATEGORIES, CONTENT_TYPES

DEMO_DAYS = 240
SEED = 20261116

# platform -> (followers at start, followers at end, base views, base eng rate, posts per week)
PLATFORM_PROFILE = {
    "youtube":   dict(f0=41_000, f1=52_800, views=14_000, eng=0.052, per_week=2.0),
    "instagram": dict(f0=28_500, f1=33_400, views=9_000,  eng=0.071, per_week=4.0),
    "x":         dict(f0=19_800, f1=21_900, views=6_500,  eng=0.034, per_week=7.0),
    "linkedin":  dict(f0=12_400, f1=17_900, views=7_800,  eng=0.046, per_week=3.0),
}
# category lift per platform (multiplier on views and engagement)
CATEGORY_FIT = {
    "youtube":   {"Tutorials": 1.45, "Behind the Scenes": 0.8, "Opinions": 1.0, "Case Studies": 1.2, "News & Trends": 0.95, "Q&A": 0.9},
    "instagram": {"Tutorials": 0.95, "Behind the Scenes": 1.5, "Opinions": 0.85, "Case Studies": 0.9, "News & Trends": 0.8, "Q&A": 1.25},
    "x":         {"Tutorials": 0.8, "Behind the Scenes": 0.85, "Opinions": 1.5, "Case Studies": 0.9, "News & Trends": 1.35, "Q&A": 1.0},
    "linkedin":  {"Tutorials": 1.0, "Behind the Scenes": 0.8, "Opinions": 1.15, "Case Studies": 1.6, "News & Trends": 1.05, "Q&A": 0.75},
}
BEST_HOURS = {"youtube": (16, 18), "instagram": (11, 13), "x": (8, 10), "linkedin": (7, 9)}
BEST_DOW = {"youtube": {5, 6, 4}, "instagram": {1, 2, 6}, "x": {1, 2, 3}, "linkedin": {1, 2, 3}}

TOPICS = [
    "RAG pipelines", "Vector databases", "AI agents", "Prompt engineering", "Fine-tuning small models",
    "Python automation", "FastAPI APIs", "React performance", "Career in AI", "Building in public",
    "LLM evals", "Model deployment", "Data cleaning", "Side projects", "Open-source tools",
]
TITLE_TEMPLATES = {
    "Tutorials": ["How to build {t} in 20 minutes", "{t} explained step by step", "Beginner's guide to {t}", "{t}: the complete walkthrough"],
    "Behind the Scenes": ["My workflow for {t}", "A day working on {t}", "What I learned shipping {t}", "Inside my setup for {t}"],
    "Opinions": ["Why {t} is overrated", "Unpopular opinion on {t}", "Stop doing {t} this way", "{t} is changing faster than you think"],
    "Case Studies": ["How we improved results with {t}: 3 lessons", "Case study: {t} in production", "{t} cut our costs by 40%", "What {t} looked like at 10x scale"],
    "News & Trends": ["This week in AI: {t}", "{t} just changed. Here is what matters", "Trend watch: {t}", "Everything new in {t}"],
    "Q&A": ["You asked: is {t} worth learning?", "Answering your questions on {t}", "Q&A: {t} edition", "Your top 5 questions about {t}"],
}


def _hour_effect(platform: str, hour: int) -> float:
    lo, hi = BEST_HOURS[platform]
    if lo <= hour <= hi:
        return 1.28
    dist = min(abs(hour - lo), abs(hour - hi))
    return max(0.72, 1.0 - 0.06 * dist)


def generate_demo(now: datetime | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Returns (content_df, followers_df, accounts). Deterministic for a given `now` date."""
    rng = np.random.default_rng(SEED)
    now = (now or datetime.now(timezone.utc)).replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(days=DEMO_DAYS)
    rows: list[dict] = []
    viral_done = False

    for platform, prof in PLATFORM_PROFILE.items():
        n_weeks = DEMO_DAYS / 7
        n_posts = int(prof["per_week"] * n_weeks)
        offsets = np.sort(rng.uniform(0, DEMO_DAYS, n_posts))
        for i, off in enumerate(offsets):
            dow_pool = list(BEST_DOW[platform]) * 2 + list(range(7))
            day_start = start + timedelta(days=float(off))
            # nudge to a preferred weekday sometimes
            if rng.random() < 0.55:
                target = int(rng.choice(dow_pool))
                day_start += timedelta(days=(target - day_start.weekday()) % 7)
                if day_start > now:
                    day_start -= timedelta(days=7)
            lo, hi = BEST_HOURS[platform]
            hour = int(rng.integers(lo, hi + 1)) if rng.random() < 0.45 else int(rng.integers(6, 23))
            published = day_start.replace(hour=hour, minute=int(rng.integers(0, 60)), second=0, microsecond=0)
            if published >= now:
                published = now - timedelta(hours=int(rng.integers(6, 72)))
            age_days = (now - published).days
            progress = 1 - age_days / DEMO_DAYS

            category = str(rng.choice(CATEGORIES, p=[0.26, 0.14, 0.18, 0.14, 0.16, 0.12]))
            ctype = str(rng.choice(CONTENT_TYPES[platform]))
            topic = str(rng.choice(TOPICS))
            title = str(rng.choice(TITLE_TEMPLATES[category])).format(t=topic)
            if rng.random() < 0.25 and not title.endswith("?"):
                title += "?"

            if platform == "youtube":
                duration = int(rng.integers(20, 58)) if ctype == "short" else int(rng.integers(360, 1500))
            elif platform == "instagram":
                duration = int(rng.integers(12, 55)) if ctype == "reel" else None
            else:
                duration = None

            fit = CATEGORY_FIT[platform][category]
            growth = 1 + 0.35 * progress                              # audience compounding
            dow_eff = 1.15 if published.weekday() in BEST_DOW[platform] else 0.95
            type_eff = {"short": 1.5, "reel": 1.35, "thread": 1.25, "carousel": 1.2, "article": 0.85}.get(ctype, 1.0)
            title_eff = (1.08 if title.endswith("?") else 1.0) * (1.06 if any(ch.isdigit() for ch in title) else 1.0)
            noise = float(rng.lognormal(0, 0.30))
            views = prof["views"] * growth * fit * _hour_effect(platform, hour) * dow_eff * type_eff * title_eff * noise

            eng = prof["eng"] * (0.85 + 0.15 * fit) * float(rng.normal(1.0, 0.10))
            if platform == "youtube" and ctype == "video" and duration and duration > 900:
                eng *= 0.9                                             # long videos: lower like-rate
            # --- the story: engagement dips in the last ~3 weeks, mostly on Instagram/LinkedIn, and
            # a sharp drop in comment rate after a switch to a lower-interaction format.
            if age_days <= 24:
                dip = {"youtube": 0.9, "instagram": 0.6, "x": 0.84, "linkedin": 0.66}[platform]
                eng *= dip
            # --- viral outlier
            if (not viral_done) and platform == "x" and 38 <= age_days <= 44 and category == "Opinions":
                views *= 9.0
                eng *= 1.25
                viral_done = True
            views = int(max(80, views))
            total_eng = max(1, int(views * max(0.004, eng)))
            likes = int(total_eng * rng.uniform(0.74, 0.86))
            comment_share = rng.uniform(0.07, 0.13) * (0.6 if (age_days <= 24 and platform in {"instagram", "linkedin"}) else 1.0)
            comments = int(total_eng * comment_share * (1.4 if category in {"Q&A", "Opinions"} else 1.0))
            shares = max(0, total_eng - likes - comments)
            gained = int(views * rng.uniform(0.0006, 0.0016) * (1.5 if category == "Tutorials" else 1.0)) \
                if platform in {"youtube", "instagram", "linkedin"} else None

            rows.append(dict(
                platform=platform, content_id=f"demo-{platform[:2]}-{i:03d}", content_type=ctype, title=title,
                published_at=published, views=views, likes=likes, comments=comments, shares=shares,
                followers_gained=gained, duration_sec=duration, category=category, topic=topic,
            ))

    content = pd.DataFrame(rows).sort_values("published_at").reset_index(drop=True)

    # daily follower series, smooth growth + weekday noise, nudged by posting activity
    days = pd.date_range(start.date(), now.date(), freq="D", tz="UTC")
    frames = []
    accounts = {}
    for platform, prof in PLATFORM_PROFILE.items():
        t = np.linspace(0, 1, len(days))
        base = prof["f0"] + (prof["f1"] - prof["f0"]) * (t ** 1.15)
        wiggle = rng.normal(0, prof["f1"] * 0.0006, len(days)).cumsum() * 0.2
        series = np.maximum.accumulate(base + wiggle).astype(int)
        frames.append(pd.DataFrame({"date": days, "platform": platform, "followers": series}))
        accounts[platform] = dict(account_label=f"@novachen.{platform}", followers=int(series[-1]))
    followers = pd.concat(frames, ignore_index=True)
    return content, followers, accounts
