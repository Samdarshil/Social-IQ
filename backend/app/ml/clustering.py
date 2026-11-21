"""Engagement clustering for YouTube trending-video data (Kaggle: datasnaek/youtube-new).

Goal: group videos by observed engagement patterns and describe each group. This is DESCRIPTIVE. Clusters summarise
what is in the historical dataset; they are not predictions of future popularity, and every video here already trended
(selection bias), so findings do not describe YouTube in general.

Method
  1. One row per video: the LAST trending record (views/likes/comments are cumulative, so this is the latest snapshot).
  2. Exclude videos that cannot show engagement: comments or ratings disabled, removed/errored, zero views.
  3. Features: log views, log likes, log comments, log engagement rate where engagement rate = (likes + comments) / views.
     Logs tame the heavy right tail; StandardScaler puts the four on one scale before distance-based clustering.
  4. KMeans (k = 3 by default for interpretability as lower / moderate / higher). The silhouette score for k = 2..8 is reported
     so the reader can see how well-separated the groups really are. A Gaussian mixture is fitted as a cross-check, and
     stability is measured by refitting on random 80% subsamples (adjusted Rand index).
  5. Clusters are ordered by the mean of their standardized centroid and named lower / moderate / higher engagement.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

FEATURES = ["log_views", "log_likes", "log_comments", "log_engagement_rate"]
FEATURE_LABELS = {"log_views": "Views", "log_likes": "Likes", "log_comments": "Comments", "log_engagement_rate": "Engagement rate"}
USECOLS = ["video_id", "trending_date", "title", "channel_title", "category_id", "publish_time", "tags", "views", "likes", "dislikes",
           "comment_count", "comments_disabled", "ratings_disabled", "video_error_or_removed"]
TIER_NAMES = {2: ["Lower engagement", "Higher engagement"], 3: ["Lower engagement", "Moderate engagement", "Higher engagement"],
              4: ["Lowest engagement", "Lower-moderate engagement", "Upper-moderate engagement", "Highest engagement"]}
SEED = 42


def read_csv(path: Path) -> pd.DataFrame:
    for enc in ("utf-8", "latin-1"):
        try:
            return pd.read_csv(path, encoding=enc, usecols=lambda c: c in USECOLS)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode {path.name}")


def prepare(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Deduplicate to one row per video and drop videos whose engagement cannot be measured. Returns (frame, accounting)."""
    acct = {"rows_raw": int(len(raw))}
    d = raw.sort_values("views").drop_duplicates("video_id", keep="last").copy()   # latest = highest cumulative views
    acct["videos_unique"] = int(len(d))
    removed = d["video_error_or_removed"].astype(bool)
    disabled = (d["comments_disabled"].astype(bool) | d["ratings_disabled"].astype(bool)) & ~removed
    zero = (d["views"] <= 0) & ~removed & ~disabled
    acct["excluded"] = {"removed_or_error": int(removed.sum()), "comments_or_ratings_disabled": int(disabled.sum()), "zero_views": int(zero.sum())}
    d = d[~(removed | disabled | zero)].copy()
    d["engagement_rate"] = (d["likes"] + d["comment_count"]) / d["views"]
    d["like_rate"] = d["likes"] / d["views"]
    d["comment_rate"] = d["comment_count"] / d["views"]
    d["dislike_share"] = d["dislikes"] / (d["likes"] + d["dislikes"]).replace(0, np.nan)
    d["log_views"] = np.log1p(d["views"])
    d["log_likes"] = np.log1p(d["likes"])
    d["log_comments"] = np.log1p(d["comment_count"])
    d["log_engagement_rate"] = np.log1p(d["engagement_rate"] * 100)
    t = pd.to_datetime(d["trending_date"], format="%y.%d.%m", errors="coerce")
    p = pd.to_datetime(d["publish_time"], errors="coerce", utc=True).dt.tz_localize(None).dt.normalize()
    d["days_to_trend"] = (t - p).dt.days.clip(lower=0)
    d["title_len"] = d["title"].fillna("").str.len()
    d["tag_count"] = d["tags"].fillna("[none]").map(lambda s: 0 if s == "[none]" else s.count("|") + 1)
    acct["videos_used"] = int(len(d))
    acct["trending_window"] = {"first": None if t.isna().all() else str(t.min().date()), "last": None if t.isna().all() else str(t.max().date())}
    return d.reset_index(drop=True), acct


def _f(x, nd=4):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), nd)


def _interpret_silhouette(s: float) -> str:
    if s >= 0.5:
        return "clear structure"
    if s >= 0.25:
        return "weak to moderate structure: groups overlap and the data looks more like a continuum than separate clusters"
    return "no meaningful cluster structure"


def analyse(raw: pd.DataFrame, cat_map: dict[int, str], country: str, k: int = 3) -> dict:
    d, acct = prepare(raw)
    if len(d) < 300:
        raise ValueError("Not enough usable videos to cluster (need at least 300).")
    cat = d["category_id"].map(cat_map).fillna("Other")
    d["category"] = cat

    X = d[FEATURES].to_numpy()
    scaler = StandardScaler().fit(X)
    Z = scaler.transform(X)
    rng = np.random.RandomState(SEED)
    sil_idx = rng.choice(len(Z), min(6000, len(Z)), replace=False)

    sil_by_k = {}
    for kk in range(2, 9):
        lab = KMeans(kk, n_init=10, random_state=SEED).fit_predict(Z)
        sil_by_k[kk] = _f(silhouette_score(Z[sil_idx], lab[sil_idx]), 3)
    km = KMeans(k, n_init=10, random_state=SEED).fit(Z)
    raw_lab = km.labels_
    cz = km.cluster_centers_
    order = np.argsort(cz.mean(axis=1))                       # lowest -> highest composite engagement
    rank = np.empty(k, dtype=int); rank[order] = np.arange(k)
    d["cluster"] = rank[raw_lab]
    cz = cz[order]

    gmm_lab = GaussianMixture(k, covariance_type="full", random_state=SEED).fit_predict(Z)
    ari_gmm = adjusted_rand_score(d["cluster"], gmm_lab)
    aris = []
    for i in range(10):
        sub = np.random.RandomState(i).choice(len(Z), int(len(Z) * 0.8), replace=False)
        m = KMeans(k, n_init=5, random_state=i).fit(Z[sub])
        aris.append(adjusted_rand_score(d["cluster"], m.predict(Z)))

    # ---- relationships between views, likes, comments
    cols = ["views", "likes", "comment_count", "engagement_rate"]
    sp = d[cols].corr(method="spearman")
    rho = lambda a, b: _f(sp.loc[a, b], 3)
    corr = {"labels": ["Views", "Likes", "Comments", "Engagement rate"], "spearman": [[_f(v, 3) for v in row] for row in sp.to_numpy()],
            "note": "Spearman rank correlation (robust to the heavy tail; no log needed)."}

    # ---- category analysis
    gl = d["engagement_rate"].median()
    rows = []
    for name, g in d.groupby("category"):
        rows.append(dict(name=name, n=int(len(g)), median_views=_f(g["views"].median(), 0), median_likes=_f(g["likes"].median(), 0),
                         median_comments=_f(g["comment_count"].median(), 0), median_engagement_rate=_f(g["engagement_rate"].median(), 4),
                         median_like_rate=_f(g["like_rate"].median(), 4), median_comment_rate=_f(g["comment_rate"].median(), 5),
                         share_higher_cluster=_f((g["cluster"] == k - 1).mean(), 3), share_lower_cluster=_f((g["cluster"] == 0).mean(), 3)))
    rows.sort(key=lambda r: -r["median_engagement_rate"])
    big = [g["engagement_rate"].to_numpy() for _, g in d.groupby("category") if len(g) >= 30]
    kw = stats.kruskal(*big) if len(big) > 1 else None
    n_kw = int(sum(len(x) for x in big))
    category = dict(rows=rows, overall_median_engagement_rate=_f(gl, 4), min_n_for_test=30,
                    kruskal=None if kw is None else dict(h=_f(kw.statistic, 1), p=float(kw.pvalue), epsilon_sq=_f(kw.statistic / max(n_kw - 1, 1), 3), categories=len(big), videos=n_kw))

    # ---- cluster profiles
    clusters = []
    names = TIER_NAMES.get(k, [f"Group {i + 1}" for i in range(k)])
    base_share = cat.value_counts(normalize=True)
    for c in range(k):
        g = d[d["cluster"] == c]
        z = dict(zip(FEATURES, cz[c]))
        scale_z = np.mean([z["log_views"], z["log_likes"], z["log_comments"]])
        rate_z = z["log_engagement_rate"]
        scale = "very large audiences" if scale_z > 0.6 else "small audiences" if scale_z < -0.6 else "mid-sized audiences"
        rate = "an above-average interaction rate" if rate_z > 0.35 else "a below-average interaction rate" if rate_z < -0.35 else "a typical interaction rate"
        top = g["category"].value_counts(normalize=True).head(6)
        tops = [dict(name=n, share=_f(s, 3), lift=_f(s / base_share[n], 2)) for n, s in top.items()]
        ex = g.sort_values("views", ascending=False).iloc[len(g) // 2: len(g) // 2 + 1]      # median-reach example, not a cherry-picked extreme
        clusters.append(dict(
            id=c, label=names[c], size=int(len(g)), share=_f(len(g) / len(d), 3), descriptor=f"{scale.capitalize()} with {rate}",
            centroid_z={FEATURE_LABELS[f]: _f(z[f], 2) for f in FEATURES},
            medians=dict(views=_f(g["views"].median(), 0), likes=_f(g["likes"].median(), 0), comments=_f(g["comment_count"].median(), 0),
                         engagement_rate=_f(g["engagement_rate"].median(), 4), like_rate=_f(g["like_rate"].median(), 4), comment_rate=_f(g["comment_rate"].median(), 5)),
            traits=dict(dislike_share=_f(g["dislike_share"].median(), 4), days_to_trend=_f(g["days_to_trend"].median(), 1),
                        title_length=_f(g["title_len"].median(), 0), tag_count=_f(g["tag_count"].median(), 0)),
            top_categories=tops,
            example=[dict(title=str(r["title"])[:80], channel=str(r["channel_title"])[:40], views=int(r["views"]), engagement_rate=_f(r["engagement_rate"], 4)) for _, r in ex.iterrows()],
        ))

    # ---- 2D projection for the scatter (PCA of the standardized features)
    pca = PCA(2, random_state=SEED).fit(Z)
    pts_idx = rng.choice(len(Z), min(1200, len(Z)), replace=False)
    P = pca.transform(Z[pts_idx])
    scatter = dict(explained_variance=[_f(v, 3) for v in pca.explained_variance_ratio_],
                   axes=[{FEATURE_LABELS[f]: _f(w, 2) for f, w in zip(FEATURES, comp)} for comp in pca.components_],
                   points=[[_f(p[0], 2), _f(p[1], 2), int(d["cluster"].iloc[i])] for p, i in zip(P, pts_idx)])

    sil_k = sil_by_k[k]
    model = dict(algorithm="KMeans", k=k, features=[FEATURE_LABELS[f] for f in FEATURES], scaling="log1p, then StandardScaler (zero mean, unit variance)",
                 silhouette_by_k=sil_by_k, silhouette=sil_k, silhouette_reading=_interpret_silhouette(sil_k or 0),
                 best_silhouette_k=max(sil_by_k, key=lambda x: sil_by_k[x]),
                 k_choice="k = 3 is used so groups read as lower / moderate / higher engagement; the silhouette curve above shows how that compares with other k.",
                 gmm_agreement_ari=_f(ari_gmm, 3), stability_ari_mean=_f(np.mean(aris), 3), stability_ari_min=_f(np.min(aris), 3),
                 pca_note="The 2D picture is a PCA projection, so it shows the shape of the data but not every distance.")

    res = dict(country=country, dataset=acct, features_definition="Engagement rate = (likes + comments) / views, using the latest trending snapshot of each video.",
               correlations=corr, category=category, model=model, clusters=clusters, scatter=scatter)
    res["takeaways"] = _takeaways(res, d, rho)
    res["caveats"] = [
        "Historical trending data (Nov 2017 to Jun 2018), not a live feed. Clusters describe this dataset and are not predictions of future popularity.",
        "Every video here trended, so it was already popular. Patterns may not hold for videos that never trended.",
        "Views, likes and comments are cumulative at the last time a video appeared on the trending list, so older videos had longer to accumulate them.",
        "Clusters are a convenient partition of a continuum, not natural species. See the silhouette score.",
        "The four features overlap by construction: views, likes and comments are strongly correlated and engagement rate is computed from all three. Distances therefore mostly reflect overall scale plus interaction rate; this is the measure set the brief suggests.",
    ]
    return res


def _pct(x):
    return f"{x * 100:.1f}%"


def _takeaways(res: dict, d: pd.DataFrame, rho) -> list[str]:
    out = []
    vl, vc, lc = rho("views", "likes"), rho("views", "comment_count"), rho("likes", "comment_count")
    ver = rho("views", "engagement_rate")
    closest = "likes and comments" if lc >= max(vl, vc) else "views and likes" if vl >= vc else "views and comments"
    out.append(f"Views, likes and comments rise together (Spearman ρ: views-likes {vl}, views-comments {vc}, likes-comments {lc}); {closest} are the most tightly linked pair.")
    strength = "weakly" if abs(ver) < 0.3 else "moderately" if abs(ver) < 0.6 else "strongly"
    direction = "negatively" if ver < 0 else "positively"
    out.append(f"Reach and interaction rate are different things: views are {strength} and {direction} related to engagement rate (ρ = {ver}), so the most-viewed videos are not automatically the ones viewers react to most.")
    rows = [r for r in res["category"]["rows"] if r["n"] >= 30]
    if len(rows) >= 2:
        hi, lo = rows[0], rows[-1]
        kw = res["category"]["kruskal"]
        eff = "small" if kw and kw["epsilon_sq"] < 0.06 else "moderate" if kw and kw["epsilon_sq"] < 0.14 else "large"
        ptxt = "< 0.001" if kw["p"] < 0.001 else "= " + format(kw["p"], ".3f")
        out.append(f"{hi['name']} has the highest median engagement rate ({_pct(hi['median_engagement_rate'])}) and {lo['name']} the lowest ({_pct(lo['median_engagement_rate'])}). "
                   f"Kruskal-Wallis p {ptxt} with a {eff} effect size (ε² = {kw['epsilon_sq']}).")
    cl = res["clusters"]
    mv = [f"{c['medians']['views']:,.0f}" for c in cl]
    me = [_pct(c["medians"]["engagement_rate"]) for c in cl]
    mono = all(cl[i]["medians"]["views"] <= cl[i + 1]["medians"]["views"] and cl[i]["medians"]["engagement_rate"] <= cl[i + 1]["medians"]["engagement_rate"] for i in range(len(cl) - 1))
    res["model"]["tiers_consistent"] = bool(mono)
    out.append(f"From lower to higher group, median views are {', '.join(mv)} and median engagement rate is {', '.join(me)}. "
               f"{'' if mono else 'The groups are not ordered the same way on reach and on rate here, so the names reflect the combined position of all four measures. '}"
               f"Silhouette {res['model']['silhouette']} means {res['model']['silhouette_reading']}.")
    hi = cl[-1]
    cand = [t for t in hi["top_categories"] if t["share"] >= 0.05]
    if cand:
        t = max(cand, key=lambda x: x["lift"])
        word = "over-represents" if t["lift"] > 1 else "is spread like the whole dataset in"
        out.append(f"Among categories making up at least 5% of the higher-engagement group, {t['name']} is the most over-represented ({_pct(t['share'])} of the group, {t['lift']}x its share of all videos)." if t["lift"] > 1.1
                   else f"The higher-engagement group's category mix is close to the whole dataset's (largest lift {t['lift']}x), so category alone does not define it.")
    kw = res["category"]["kruskal"]
    if kw and kw["epsilon_sq"] >= 0.06:
        out.append("For creators: interaction rate and reach are separate wins in trending data. Judge a video against others in its own category, because category sets the baseline for a good engagement rate.")
    else:
        out.append("For creators: interaction rate and reach are separate wins in trending data. Category differences are small here, so format and audience matter more than topic alone.")
    return out
