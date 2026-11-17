# YouTube trending engagement analysis

This is the analysis the hackathon brief asks for: cluster YouTube trending videos by engagement and describe the groups.
It is **descriptive**. Clusters summarise patterns in historical data; they are not predictions of future popularity.

- Code: `backend/app/ml/clustering.py` (pipeline), `backend/app/services/trending.py` (loader), `backend/app/api/research.py` (API), `frontend/src/pages/Clusters.tsx` (page)
- Tests: `backend/tests/test_trending.py`
- Data: Kaggle [YouTube Trending Video Dataset](https://www.kaggle.com/datasets/datasnaek/youtube-new), 10 countries, trending dates 2017-11-14 to 2018-06-14

## Method

1. **One row per video.** Trending files repeat a video on every day it trended. Views, likes and comments are cumulative, so the last record (highest views) is kept: 40,949 US rows become 6,351 unique videos.
2. **Exclusions.** Videos whose engagement cannot be measured are dropped and counted: comments or ratings disabled, removed or errored, zero views (US: 122 dropped, 6,229 used).
3. **Features.** `log(1 + views)`, `log(1 + likes)`, `log(1 + comments)`, `log(1 + 100 x engagement rate)` where engagement rate = (likes + comments) / views. Logs tame the heavy right tail.
4. **Scaling.** `StandardScaler` so every feature has zero mean and unit variance before distance-based clustering.
5. **Clustering.** KMeans, `k = 3` (so groups read as lower, moderate, higher engagement), `n_init = 10`, fixed seed. Silhouette is reported for `k = 2..8` so separation is visible rather than assumed.
6. **Cross-checks.** A Gaussian mixture on the same features (agreement by adjusted Rand index) and stability from 10 refits on random 80% subsamples.
7. **Naming.** Clusters are ordered by the mean of their standardised centroid and named lower, moderate, higher. When the ordering by median views and by median engagement rate disagree (it does in some countries), the page says so.
8. **Characteristics.** Each group is profiled with medians (views, likes, comments, engagement rate), dislike share, days from publication to trending, title length, tag count, and category lift (share in group / share overall). Dislikes, timing, title and tags are profile variables only; they are not clustered on.

## Answers to the guiding questions (United States)

**How does engagement vary across categories?** Substantially. Highest median engagement rate: Howto & Style 4.3%, Music 3.8%, Education 3.8%. Lowest: News & Politics 1.5%, Sports 1.3%, Autos & Vehicles 1.2%. Kruskal-Wallis p < 0.001, effect size ε² = 0.191 (large).

**What relationships exist between views, likes and comments?** Strong and monotonic. Spearman ρ: views-likes 0.879, views-comments 0.845, likes-comments 0.892. Engagement *rate* is almost unrelated to views (ρ = 0.077): reach and interaction rate are different things.

**Can videos be grouped into distinct engagement patterns?** Only weakly. Silhouette at k = 3 is 0.313 (k = 2 scores 0.39). The groups overlap; the data is closer to a continuum than to separate clusters. The partition is stable (ARI 0.948 across subsamples) but agrees little with a Gaussian mixture (ARI 0.097), so boundaries depend on the algorithm.

**What characteristics distinguish the groups?**

| Group | Videos | Median views | Median likes | Median comments | Median engagement rate | Median dislike share |
|---|---|---|---|---|---|---|
| Lower engagement | 921 (15%) | 28,964 | 264 | 58 | 1.05% | 7.6% |
| Moderate engagement | 3,103 (50%) | 350,226 | 7,399 | 855 | 2.56% | 3.7% |
| Higher engagement | 2,205 (35%) | 1,970,963 | 61,134 | 6,284 | 3.89% | 2.6% |

Higher engagement skews to Music and Comedy; lower engagement skews to News & Politics and Sports. See the page for category lifts and the other traits.

**What could creators take from it?** Interaction rate and reach are separate wins; judge a video against its own category because category sets the baseline for a good engagement rate. These are observations about trending videos, not guarantees.

## Results across all ten countries (k = 3)

| Country | Videos used | Silhouette | Stability (ARI) | Median engagement rate | Group sizes (lower / moderate / higher) |
|---|---|---|---|---|---|
| United States | 6,229 | 0.31 | 0.95 | 2.8% | 921 / 3,103 / 2,205 |
| United Kingdom | 3,213 | 0.32 | 0.94 | 2.7% | 981 / 1,066 / 1,166 |
| Canada | 23,888 | 0.30 | 0.97 | 2.6% | 4,933 / 11,429 / 7,526 |
| Germany | 28,499 | 0.35 | 0.99 | 3.0% | 7,894 / 8,166 / 12,439 |
| France | 29,572 | 0.36 | 0.99 | 3.0% | 9,729 / 8,716 / 11,127 |
| India | 15,524 | 0.40 | 0.92 | 0.9% | 8,375 / 2,940 / 4,209 |
| Japan | 11,531 | 0.34 | 0.93 | 1.5% | 3,881 / 5,581 / 2,069 |
| South Korea | 14,987 | 0.34 | 0.99 | 1.5% | 5,857 / 4,230 / 4,900 |
| Mexico | 32,682 | 0.37 | 0.99 | 3.5% | 13,201 / 9,592 / 9,889 |
| Russia | 32,521 | 0.35 | 0.98 | 4.7% | 9,825 / 9,438 / 13,258 |

Separation is weak to moderate everywhere (0.30 to 0.40), which is consistent with a continuum.

## Limitations

- Historical data (Nov 2017 to Jun 2018), not a live feed.
- Every video trended, so it was already popular (selection bias). Findings do not describe YouTube overall.
- Counts are cumulative at the last trending appearance, so older videos had longer to accumulate them.
- The four clustering features overlap by construction (views, likes and comments correlate at ρ 0.85 to 0.89, and engagement rate is computed from all three), so distances mostly reflect overall scale plus interaction rate. This is the measure set the brief suggests.
- Engagement rate counts likes and comments only (the dataset has no shares or watch time).
- The US file has 6,351 unique videos; other countries have more or fewer, so country comparisons are indicative only.
- The data is not committed to this repository. Numbers in the app come from pre-computed snapshots built from the Kaggle CSVs, or are computed live if you place the CSVs in `backend/data/kaggle_youtube/`.

## Reproduce

```bash
# 1. download the Kaggle dataset and put the CSVs here (names like USvideos.csv or USvideos_1.csv):
mkdir -p backend/data/kaggle_youtube
# also copy the <CC>_category_id.json files there (optional: a merged category map ships in the repo)

# 2. rebuild the committed snapshots (about 1 minute for all countries)
python scripts/build_trending_snapshots.py

# 3. or just run the app; with the CSVs present it computes live and shows "computed live from CSV"
```

Set `YT_TRENDING_DIR` to use another folder.
