# Machine learning

SocialIQ has two ML components.

1. **Engagement clustering** of YouTube trending videos (unsupervised, descriptive): see [TRENDING_ANALYSIS.md](TRENDING_ANALYSIS.md).
2. **Creator performance simulator** (supervised, below).

## Creator performance simulator

**Target.** Performance Score (0–100) = 50% within-platform percentile of views + 50% within-platform percentile of engagement rate. Bands: HIGH ≥ 67, MEDIUM 34–66, LOW < 34.

**Features (leakage-safe).** Platform, category, content type, duration, title descriptors, publish hour/weekday, plus history features computed only from *earlier* posts on the same platform and creator-wide momentum. Nothing from the post being predicted or its future is used.

**Validation.** Chronological 80/20 split. Model choice by `TimeSeriesSplit` cross-validation among a platform-mean baseline, Ridge, RandomForest, GradientBoosting and XGBoost. Uncertainty: split-conformal 80% interval calibrated on the newest 15% of the development set. Explanations: SHAP TreeExplainer, grouped into human-readable factors. Recommendations are what-if changes re-scored by the model.

## Results on the demo dataset (547 posts: 437 dev, 110 test)
| Model | CV MAE | CV R² |
|---|---|---|
| Platform-mean baseline | 19.1 ± 1.0 | −0.05 |
| Ridge | 17.7 ± 0.7 | 0.07 |
| **RandomForest (selected)** | **16.8 ± 1.2** | **0.15** |
| GradientBoosting | 17.9 ± 1.8 | 0.01 |
| XGBoost | 17.3 ± 1.3 | 0.09 |

Held-out test: MAE 20.04 (baseline 20.08), RMSE 23.2, R² −0.014, Spearman 0.50, bias +11.2, top-third hit rate 59.5%, interval half-width 32.0 with 82.7% empirical coverage.

## Honest reading
The model ranks posts better than chance (Spearman 0.50) but does **not** meaningfully beat the baseline on absolute error. The demo data is synthetic, so these numbers describe the pipeline, not real creators. The UI shows this in the Model Card; predictions are estimates with an interval, not guarantees. With fewer than 60 posts the API returns 422 rather than training.
