"""Training, evaluation, prediction and SHAP explanations for the Performance Score model.

Protocol (all chronological, no shuffling):
  * dev = oldest 80% of posts, test = newest 20%.
  * Model selection: TimeSeriesSplit CV on dev, scored by MAE; target reference refit inside each fold.
  * Interval calibration: chosen model fit on the older 85% of dev, residuals on the newest 15% of dev
    give a split-conformal 80% interval half-width. Empirical coverage is then measured on the untouched test set.
  * Deployed model: refit on all posts (more data), same hyper-parameters.
Nothing here is hard-coded: every reported number comes from this run.
"""
from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import shap
from scipy.stats import spearmanr
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.features import (ALL_CATEGORIES, GROUPS, creator_features, NUMERIC, build_training_frame, design_matrix, fit_reference,
                             followers_at, history_features, target_score, _static)
from app.schemas.content import CONTENT_TYPES, PLATFORM_LABELS
from app.services.dataset import Workspace

try:
    from xgboost import XGBRegressor
    HAVE_XGB = True
except Exception:  # pragma: no cover
    HAVE_XGB = False

MIN_POSTS = 60
SEED = 7
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def classify(score: float) -> str:
    return "HIGH" if score >= 67 else "MEDIUM" if score >= 34 else "LOW"


def _candidates() -> dict:
    c = {
        "RandomForest": lambda: RandomForestRegressor(n_estimators=300, min_samples_leaf=3, max_features=0.5, n_jobs=-1, random_state=SEED),
        "GradientBoosting": lambda: GradientBoostingRegressor(n_estimators=250, learning_rate=0.04, max_depth=3, subsample=0.8, random_state=SEED),
    }
    if HAVE_XGB:
        c["XGBoost"] = lambda: XGBRegressor(n_estimators=250, learning_rate=0.04, max_depth=3, subsample=0.8, colsample_bytree=0.8,
                                            random_state=SEED, n_jobs=2, verbosity=0)
    return c


def _baselines() -> dict:
    return {
        "Baseline: platform average": lambda: DummyRegressor(strategy="mean"),
        "Baseline: Ridge regression": lambda: make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 12))),
    }


@dataclass
class Bundle:
    model: object
    model_name: str
    columns: list[str]
    medians: dict
    ref: dict
    explainer: object
    base_value: float
    conformal_q: float
    card: dict
    trained_rows: int
    lock: threading.Lock = field(default_factory=threading.Lock)


def _impute(X: pd.DataFrame, medians: dict | None = None) -> tuple[pd.DataFrame, dict]:
    X = X.copy()
    medians = medians or {c: (float(X[c].median()) if X[c].notna().any() else 0.0) for c in X.columns}
    return X.fillna(medians), medians


def _metrics(y, p) -> dict:
    return dict(mae=float(mean_absolute_error(y, p)), rmse=float(math.sqrt(mean_squared_error(y, p))), r2=float(r2_score(y, p)),
                spearman=float(spearmanr(y, p).correlation))


def train(ws: Workspace) -> Bundle:
    if len(ws.content) < MIN_POSTS:
        raise ValueError(f"Need at least {MIN_POSTS} posts to train a reliable model; found {len(ws.content)}. "
                         "Connect more data or explore the demo workspace.")
    frame = build_training_frame(ws)
    n = len(frame)
    cut = int(n * 0.8)
    dev, test = frame.iloc[:cut].reset_index(drop=True), frame.iloc[cut:].reset_index(drop=True)

    # ---- model selection (time-series CV on dev)
    cv_rows = {}
    tscv = TimeSeriesSplit(n_splits=4)
    for name, make in {**_baselines(), **_candidates()}.items():
        maes, r2s = [], []
        for tr_i, va_i in tscv.split(dev):
            tr, va = dev.iloc[tr_i], dev.iloc[va_i]
            ref = fit_reference(tr)
            Xtr, med = _impute(design_matrix(tr))
            Xva, _ = _impute(design_matrix(va), med)
            m = make().fit(Xtr, target_score(tr, ref))
            yv, pv = target_score(va, ref), np.clip(m.predict(Xva), 0, 100)
            maes.append(mean_absolute_error(yv, pv))
            r2s.append(r2_score(yv, pv))
        cv_rows[name] = dict(cv_mae=float(np.mean(maes)), cv_mae_std=float(np.std(maes)), cv_r2=float(np.mean(r2s)))
    cand_names = list(_candidates())
    chosen = min(cand_names, key=lambda k: cv_rows[k]["cv_mae"])

    # ---- conformal calibration + held-out test
    c2 = int(len(dev) * 0.85)
    fit_part, cal_part = dev.iloc[:c2], dev.iloc[c2:]
    ref_fit = fit_reference(fit_part)
    Xf, med_f = _impute(design_matrix(fit_part))
    m_eval = _candidates()[chosen]().fit(Xf, target_score(fit_part, ref_fit))
    Xc, _ = _impute(design_matrix(cal_part), med_f)
    resid = np.abs(target_score(cal_part, ref_fit) - np.clip(m_eval.predict(Xc), 0, 100))
    k = min(len(resid), math.ceil((len(resid) + 1) * 0.8))
    q = float(np.sort(resid)[k - 1])
    Xt, _ = _impute(design_matrix(test), med_f)
    yt, pt = target_score(test, ref_fit), np.clip(m_eval.predict(Xt), 0, 100)
    coverage = float(np.mean(np.abs(yt - pt) <= q))
    test_metrics = _metrics(yt, pt)
    test_metrics["bias"] = float(np.mean(pt - yt))  # >0: model over-predicts on the newest period
    top_pred = pt >= np.quantile(pt, 2 / 3)
    test_metrics["top_third_hit_rate"] = float(np.mean(yt[top_pred] >= np.quantile(yt, 2 / 3))) if top_pred.any() else None
    base_pred = np.full(len(yt), target_score(fit_part, ref_fit).mean())
    test_metrics["baseline_mae"] = float(mean_absolute_error(yt, base_pred))
    test_metrics["mae_improvement_pct"] = float((1 - test_metrics["mae"] / test_metrics["baseline_mae"]) * 100)

    # ---- deployed model on all data
    ref_all = fit_reference(frame)
    X_all, med_all = _impute(design_matrix(frame))
    y_all = target_score(frame, ref_all)
    final = _candidates()[chosen]().fit(X_all, y_all)
    explainer = shap.TreeExplainer(final)
    sv = explainer.shap_values(X_all.sample(min(200, len(X_all)), random_state=SEED))
    mean_abs = pd.Series(np.abs(sv).mean(axis=0), index=X_all.columns)
    global_imp = sorted(({"group": g, "importance": float(mean_abs[[c for c in cols if c in mean_abs.index]].sum())} for g, cols in GROUPS.items()),
                        key=lambda d: -d["importance"])
    bv = explainer.expected_value
    base_value = float(np.ravel(bv)[0])

    card = dict(
        selected_model=chosen, xgboost_available=HAVE_XGB, target="Performance Score (0-100): 50% percentile of views + 50% percentile of engagement rate, within platform",
        classes="HIGH >= 67, MEDIUM 34-66, LOW < 34 (score terciles by construction)",
        n_posts=int(n), n_dev=int(len(dev)), n_test=int(len(test)), split="Chronological: oldest 80% dev, newest 20% test",
        candidates=[dict(name=k, **v, selected=(k == chosen)) for k, v in cv_rows.items()],
        test=test_metrics, interval=dict(level=0.8, half_width=q, empirical_test_coverage=coverage, method="split conformal on newest 15% of dev"),
        global_importance=global_imp[:8], trained_at=datetime.now(timezone.utc).isoformat(),
        data_mode=ws.source.mode,
        leakage_controls=["History features use only earlier posts on the same platform",
                          "Score reference curves fit on training rows only",
                          "No same-post metrics (likes/comments/shares) are used as inputs",
                          "Chronological split, never shuffled"],
        caveats=["The newest posts can differ systematically from older ones (e.g. an engagement dip); check 'bias' before trusting absolute scores.",
                 "Ranking quality (Spearman, top-third hit rate) is more reliable than absolute error on small datasets.",
                 "Performance Score is relative to your own history on that platform.",
                 "Small datasets give noisy estimates; the interval shows typical error, not a guarantee."])
    return Bundle(final, chosen, list(X_all.columns), med_all, ref_all, explainer, base_value, q, card, n)


# ---------------------------------------------------------------- registry
_REG: dict[str, Bundle] = {}
_REG_LOCK = threading.Lock()


def get_bundle(ws: Workspace) -> Bundle:
    with _REG_LOCK:
        b = _REG.get(ws.key)
    if b is not None:
        return b
    b = train(ws)
    with _REG_LOCK:
        for k in [k for k in _REG if k.split(":")[0:2] == ws.key.split(":")[0:2] and k != ws.key]:
            _REG.pop(k, None)
        _REG[ws.key] = b
    return b


# ---------------------------------------------------------------- prediction
def _row(ws: Workspace, spec: dict) -> pd.DataFrame:
    p, when = spec["platform"], pd.Timestamp(spec["publish_at"])
    when = when.tz_localize("UTC") if when.tzinfo is None else when.tz_convert("UTC")
    hist = ws.content[(ws.content["platform"] == p) & (ws.content["published_at"] < when)].sort_values("published_at")
    cat = spec["category"] if spec["category"] in ALL_CATEGORIES else "General"
    row = dict(title=spec.get("title", ""), hour=when.hour, dow=when.dayofweek, duration_sec=spec.get("duration_sec"))
    all_prior = ws.content[ws.content["published_at"] < when].sort_values("published_at")
    feats = _static(row) | history_features(hist, cat, when) | creator_features(all_prior, hist)
    feats["followers_log"] = float(np.log1p(followers_at(ws, p, when)))
    return pd.DataFrame([dict(platform=p, content_type=spec["content_type"], category=cat, **feats)])


def _score_rows(b: Bundle, frame: pd.DataFrame) -> np.ndarray:
    X, _ = _impute(design_matrix(frame)[b.columns], b.medians)
    return np.clip(b.model.predict(X), 0, 100)


def _fmt(col: str, row: pd.Series, spec: dict) -> str:
    return ""


def _group_explanation(group: str, row: pd.Series, spec: dict, impact: float) -> str:
    when = pd.Timestamp(spec["publish_at"])
    label = PLATFORM_LABELS.get(spec["platform"], spec["platform"])
    if group == "Publishing time":
        return f"Publishing {DOW[when.dayofweek]} at {when.hour:02d}:00 UTC"
    if group == "Platform":
        return f"Posting on {label}"
    if group == "Format":
        d = f", {int(spec['duration_sec'])}s" if spec.get("duration_sec") else ""
        return f"Format: {spec['content_type']}{d}"
    if group == "Topic category":
        return f"Topic category: {spec['category']}"
    if group == "Title style":
        bits = [b for b, k in (("question", "has_question"), ("number", "has_number"), ("emoji", "has_emoji")) if row.get(k, 0)]
        return f"Title style ({len(spec.get('title', ''))} chars{', with ' + ' & '.join(bits) if bits else ''})"
    if group == "Audience size":
        return f"Audience size on {label}"
    if group == "Recent reach on this platform":
        return f"Your recent reach on {label}"
    if group == "Recent engagement on this platform":
        return f"Your recent engagement on {label}"
    if group == "Engagement trend":
        t = row.get("h_er_trend", 0)
        return f"Engagement trend on {label} ({'rising' if t > 0 else 'falling' if t < 0 else 'flat'})"
    if group == "Track record in this category":
        n = int(row.get("h_cat_n", 0))
        return f"Your track record with {spec['category']} on {label} ({n} past posts)"
    if group == "Posting cadence":
        return f"Posting cadence ({row.get('h_gap_days', 0):.1f} days since your last {label} post)"
    return group


def predict(ws: Workspace, spec: dict, explain: bool = True, whatif: bool = True) -> dict:
    b = get_bundle(ws)
    frame = _row(ws, spec)
    score = float(_score_rows(b, frame)[0])
    lo, hi = max(0.0, score - b.conformal_q), min(100.0, score + b.conformal_q)
    out = dict(score=round(score, 1), label=classify(score), interval=dict(low=round(lo, 1), high=round(hi, 1), level=0.8,
               half_width=round(b.conformal_q, 1), empirical_test_coverage=b.card["interval"]["empirical_test_coverage"]),
               model=b.model_name, spec=spec)
    if explain:
        X, _ = _impute(design_matrix(frame)[b.columns], b.medians)
        sv = np.ravel(b.explainer.shap_values(X))
        s = pd.Series(sv, index=b.columns)
        row = frame.iloc[0]
        factors = []
        for g, cols in GROUPS.items():
            impact = float(s[[c for c in cols if c in s.index]].sum())
            factors.append(dict(group=g, impact=round(impact, 2), text=_group_explanation(g, row, spec, impact)))
        factors = [f for f in factors if abs(f["impact"]) >= 0.4]
        out["explanation"] = dict(
            base_score=round(b.base_value, 1),
            positive=sorted([f for f in factors if f["impact"] > 0], key=lambda f: -f["impact"])[:4],
            negative=sorted([f for f in factors if f["impact"] < 0], key=lambda f: f["impact"])[:4],
            method="SHAP (TreeExplainer) on the deployed model; impacts are score points relative to the average prediction.")
    if whatif:
        out["recommendations"] = _recommendations(ws, b, spec, score)
    return out


def _recommendations(ws: Workspace, b: Bundle, spec: dict, base: float) -> list[dict]:
    """Model-evaluated alternatives: each suggestion is a re-prediction with exactly one input changed."""
    recs = []
    when = pd.Timestamp(spec["publish_at"])
    when = when.tz_localize("UTC") if when.tzinfo is None else when.tz_convert("UTC")
    def batch(variants: list[dict]) -> list[float]:
        frames = pd.concat([_row(ws, {**spec, **v}) for v in variants], ignore_index=True)
        return [float(x) for x in _score_rows(b, frames)]

    def pred(**chg) -> float:
        return batch([chg])[0]

    hour_specs = [dict(publish_at=when.replace(hour=h)) for h in range(24)]
    hours = dict(zip(range(24), batch(hour_specs)))
    h_best = max(hours, key=hours.get)
    if hours[h_best] - base >= 2 and h_best != when.hour:
        recs.append(dict(kind="time", text=f"Publish around {h_best:02d}:00 UTC instead of {when.hour:02d}:00", delta=round(hours[h_best] - base, 1),
                         change=dict(publish_at=when.replace(hour=h_best).isoformat())))
    day_specs = [dict(publish_at=when + pd.Timedelta(days=(d - when.dayofweek))) for d in range(7)]
    days = dict(zip(range(7), batch(day_specs)))
    d_best = max(days, key=days.get)
    if days[d_best] - base >= 2 and d_best != when.dayofweek:
        recs.append(dict(kind="day", text=f"{DOW[d_best]} is a stronger day than {DOW[when.dayofweek]} for this post", delta=round(days[d_best] - base, 1),
                         change=dict(publish_at=(when + pd.Timedelta(days=(d_best - when.dayofweek))).isoformat())))
    cat_names = [c for c in ALL_CATEGORIES if c != "General"]
    cats = dict(zip(cat_names, batch([dict(category=c) for c in cat_names])))
    c_best = max(cats, key=cats.get)
    if cats[c_best] - base >= 3 and c_best != spec["category"]:
        recs.append(dict(kind="category", text=f"Framing this as {c_best} is predicted to perform better on {PLATFORM_LABELS[spec['platform']]}",
                         delta=round(cats[c_best] - base, 1), change=dict(category=c_best)))
    t = spec.get("title", "")
    if t:
        tv = {}
        if "?" not in t:
            tv["q"] = t.rstrip(".!") + "?"
        if not any(ch.isdigit() for ch in t):
            tv["n"] = "5 " + t
        if tv:
            sc = dict(zip(tv, batch([dict(title=v) for v in tv.values()])))
            if "q" in tv and sc["q"] - base >= 1.5:
                recs.append(dict(kind="title", text="Phrasing the title as a question is predicted to help", delta=round(sc["q"] - base, 1), change=dict(title=tv["q"])))
            if "n" in tv and sc["n"] - base >= 1.5:
                recs.append(dict(kind="title", text="Adding a number to the title is predicted to help", delta=round(sc["n"] - base, 1), change=dict(title=tv["n"])))
    alt_types = [ty for ty in CONTENT_TYPES.get(spec["platform"], []) if ty != spec["content_type"]]
    if alt_types:
        alts = dict(zip(alt_types, batch([dict(content_type=ty) for ty in alt_types])))
        ty = max(alts, key=alts.get)
        if alts[ty] - base >= 3:
            recs.append(dict(kind="format", text=f"A {ty} is predicted to outperform a {spec['content_type']} here", delta=round(alts[ty] - base, 1), change=dict(content_type=ty)))
    recs.sort(key=lambda r: -r["delta"])
    return recs[:4]


def model_card(ws: Workspace) -> dict:
    return get_bundle(ws).card


def best_ideas(ws: Workspace, platform: str | None = None, when: datetime | None = None, top: int = 5) -> list[dict]:
    """Score every (platform x category x format) combination at its best hour and return the highest predicted ones."""
    b = get_bundle(ws)
    when = pd.Timestamp(when or datetime.now(timezone.utc)) + pd.Timedelta(days=1)
    when = when.tz_localize("UTC") if when.tzinfo is None else when.tz_convert("UTC")
    rows = []
    plats = [platform] if platform else ws.platforms
    for p in plats:
        for cat in ALL_CATEGORIES:
            if cat == "General":
                continue
            for ty in CONTENT_TYPES[p]:
                for h in range(6, 22, 1):
                    spec = dict(platform=p, category=cat, content_type=ty, publish_at=when.replace(hour=h, minute=0).isoformat(),
                                title="", duration_sec=45 if ty in ("short", "reel") else None)
                    rows.append(spec)
    frames = pd.concat([_row(ws, s) for s in rows], ignore_index=True)
    scores = _score_rows(b, frames)
    df = pd.DataFrame(rows)
    df["score"] = scores
    best = df.sort_values("score", ascending=False).drop_duplicates(["platform", "category", "content_type"]).head(top)
    return [dict(platform=r.platform, category=r.category, content_type=r.content_type, hour=pd.Timestamp(r.publish_at).hour,
                 day=DOW[pd.Timestamp(r.publish_at).dayofweek], score=round(float(r.score), 1)) for r in best.itertuples()]
