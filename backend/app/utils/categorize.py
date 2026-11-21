"""Keyword-based category inference for live content (platforms do not expose our categories).
This is a transparent heuristic and is flagged in content metadata as `category_source: heuristic`."""
from __future__ import annotations

import re

RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Q&A", ("q&a", "ask me", "you asked", "your questions", "faq", "answering")),
    ("Tutorials", ("how to", "tutorial", "step by step", "guide", "walkthrough", "learn", "build", "explained", "beginner")),
    ("Case Studies", ("case study", "lessons", "results", "we improved", "how we", "cut our", "grew", "at scale")),
    ("News & Trends", ("this week", "news", "just launched", "released", "trend", "announce", "new in", "update")),
    ("Opinions", ("opinion", "overrated", "stop ", "unpopular", "why i", "hot take", "myth", "i think")),
    ("Behind the Scenes", ("behind the scenes", "my workflow", "my setup", "day in", "a day ", "what i learned", "inside")),
]


def infer_category(text: str) -> str:
    t = (text or "").lower()
    for cat, kws in RULES:
        if any(k in t for k in kws):
            return cat
    return "General"


def title_features(title: str) -> dict:
    t = title or ""
    words = re.findall(r"\w+", t)
    return {
        "title_len": len(t),
        "title_words": len(words),
        "has_question": int("?" in t),
        "has_number": int(any(c.isdigit() for c in t)),
        "has_emoji": int(bool(re.search(r"[\U0001F300-\U0001FAFF☀-➿]", t))),
        "hashtags": t.count("#"),
        "is_caps_heavy": int(sum(1 for c in t if c.isupper()) > 0.4 * max(1, len(t))),
    }
