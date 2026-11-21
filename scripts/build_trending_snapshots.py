"""Build pre-computed clustering snapshots from the Kaggle trending CSVs.

    python scripts/build_trending_snapshots.py [csv_dir]      # default backend/data/kaggle_youtube

Writes backend/app/ml/snapshots/yt_trending_<CC>.json and index.json. Commit the snapshots so the app works without the
(large) raw CSVs; the raw files are never committed.
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
if len(sys.argv) > 1:
    os.environ["YT_TRENDING_DIR"] = sys.argv[1]

from app.services import trending  # noqa: E402

index = []
for cc in trending.COUNTRIES:
    if not trending.raw_csv(cc):
        print(f"skip {cc}: no CSV in {trending.raw_dir()}")
        continue
    t = time.time()
    res = trending.compute.__wrapped__(cc)
    res.pop("source", None)
    (trending.SNAP_DIR / f"yt_trending_{cc}.json").write_text(json.dumps(res, separators=(",", ":"), ensure_ascii=False))
    m = res["model"]
    index.append(dict(country=cc, videos=res["dataset"]["videos_used"], silhouette=m["silhouette"], stability_ari=m["stability_ari_mean"],
                      median_engagement_rate=res["category"]["overall_median_engagement_rate"],
                      sizes=[c["size"] for c in res["clusters"]]))
    print(f"{cc}: {res['dataset']['videos_used']} videos, silhouette {m['silhouette']}, stability {m['stability_ari_mean']} ({time.time() - t:.1f}s)")
(trending.SNAP_DIR / "index.json").write_text(json.dumps(index, indent=1))
