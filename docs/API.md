# API reference

Generated from the FastAPI app (`app.openapi()`); interactive docs are at `/docs` when `SOCIALIQ_ENV` is not `production`.

All routes except those marked **public** require `Authorization: Bearer <token>` (from `/api/auth/login`, `/register` or `/demo`).

| Method | Path | Auth |
|---|---|---|
| GET | `/api/anomalies` | bearer |
| POST | `/api/assistant/chat` | bearer |
| GET | `/api/assistant/tools` | bearer |
| POST | `/api/auth/demo` | public |
| POST | `/api/auth/login` | public |
| GET | `/api/auth/me` | bearer |
| POST | `/api/auth/register` | public |
| GET | `/api/best-times` | bearer |
| GET | `/api/categories` | bearer |
| GET | `/api/connect/{platform}/callback` | public |
| POST | `/api/connect/{platform}/start` | bearer |
| DELETE | `/api/connections/{platform}` | bearer |
| POST | `/api/connections/{platform}/sync` | bearer |
| GET | `/api/content` | bearer |
| GET | `/api/content/top` | bearer |
| GET | `/api/content/{content_id}` | bearer |
| GET | `/api/cross-platform` | bearer |
| GET | `/api/engagement-breakdown` | bearer |
| GET | `/api/engagement-change` | bearer |
| GET | `/api/health` | public |
| GET | `/api/insights` | bearer |
| GET | `/api/ml/ideas` | bearer |
| GET | `/api/ml/model-card` | bearer |
| POST | `/api/ml/predict` | bearer |
| POST | `/api/ml/predict/batch` | bearer |
| GET | `/api/platforms` | bearer |
| GET | `/api/platforms/compare` | bearer |
| DELETE | `/api/privacy/account` | bearer |
| DELETE | `/api/privacy/data` | bearer |
| GET | `/api/privacy/export` | bearer |
| GET | `/api/privacy/overview` | bearer |
| GET | `/api/profile` | bearer |
| GET | `/api/research/trending/countries` | bearer |
| GET | `/api/research/trending/{country}` | bearer |
| GET | `/api/source` | bearer |
| GET | `/api/summary` | bearer |
| GET | `/api/timeseries` | bearer |

## Notes

- **Trending clusters** (`GET /api/research/trending/{country}`): the engagement-clustering result for one country (`US, GB, CA, DE, FR, IN, JP, KR, MX, RU`): dataset accounting, correlations, category table, silhouette curve, cluster profiles, 2D projection, takeaways and limitations. `source.kind` is `raw_csv` (computed live) or `snapshot`. See [TRENDING_ANALYSIS.md](TRENDING_ANALYSIS.md).
- **Filters**: analytics routes accept `days`, `platforms` (comma-separated), `category`, `content_type`.
- **Demo sessions** (`/api/auth/demo`) get synthetic creator data labelled `DEMO DATA`; they cannot connect, export or delete real data. The trending-cluster endpoints use real Kaggle data and are available to every signed-in user.
- **Errors** are JSON `{"detail": "..."}`: 401 unauthenticated, 404 unknown country, 409 demo restriction, 422 validation or not enough data, 429 rate limit, 503 platform not configured.
- **Assistant** (`POST /api/assistant/chat`) returns `answer`, `cards`, `tool_calls`, `mode` (`llm` or `local`), `provider`, `mode_label` and an optional `notice` explaining any fallback.
- **Creator ML** (`/api/ml/*`) refuses with 422 when fewer than 60 posts exist rather than fabricating a model.
