from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import filters, workspace
from app.ml import pipeline as ml
from app.schemas.api import BatchPredictIn, PredictIn
from app.services import analytics as A
from app.services.analytics import Filters, clean
from app.services.dataset import Workspace

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/source")
def source(ws: Workspace = Depends(workspace)):
    return dict(source=ws.source.model_dump(), creator=ws.creator_name, posts=int(len(ws.content)), notes=ws.notes)


@router.get("/summary")
def summary(f: Filters = Depends(filters), ws: Workspace = Depends(workspace)):
    return A.summary(ws, f)


@router.get("/timeseries")
def timeseries(freq: str = Query("W", pattern="^[DWM]$"), f: Filters = Depends(filters), ws: Workspace = Depends(workspace)):
    return A.timeseries(ws, f, freq)


@router.get("/platforms/compare")
def platforms_compare(f: Filters = Depends(filters), ws: Workspace = Depends(workspace)):
    return A.platform_comparison(ws, f)


@router.get("/content")
def content(sort: str = Query("published_at", pattern="^(published_at|views|engagement_rate|perf_index)$"), search: str | None = Query(None, max_length=80),
            limit: int = Query(100, ge=1, le=300), f: Filters = Depends(filters), ws: Workspace = Depends(workspace)):
    return A.content_list(ws, f, sort, limit, search)


@router.get("/content/top")
def top(n: int = Query(5, ge=1, le=20), worst: bool = False, f: Filters = Depends(filters), ws: Workspace = Depends(workspace)):
    return A.top_content(ws, f, n, worst)


@router.get("/content/{content_id}")
def content_detail(content_id: str, ws: Workspace = Depends(workspace)):
    d = A.content_details(ws, content_id)
    if d is None:
        raise HTTPException(404, "Content not found.")
    return d


@router.get("/best-times")
def best_times(f: Filters = Depends(filters), ws: Workspace = Depends(workspace)):
    return A.best_publish_times(ws, f)


@router.get("/categories")
def categories(f: Filters = Depends(filters), ws: Workspace = Depends(workspace)):
    return A.analyze_categories(ws, f)


@router.get("/engagement-breakdown")
def breakdown(f: Filters = Depends(filters), ws: Workspace = Depends(workspace)):
    return A.engagement_breakdown(ws, f)


@router.get("/engagement-change")
def engagement_change(days: int = Query(28, ge=7, le=90), f: Filters = Depends(filters), ws: Workspace = Depends(workspace)):
    return A.explain_engagement_change(ws, days, f.platforms)


@router.get("/anomalies")
def anomalies(f: Filters = Depends(filters), ws: Workspace = Depends(workspace)):
    return A.detect_anomalies(ws, f)


@router.get("/cross-platform")
def cross(f: Filters = Depends(filters), ws: Workspace = Depends(workspace)):
    return A.cross_platform(ws, f)


@router.get("/profile")
def profile(f: Filters = Depends(filters), ws: Workspace = Depends(workspace)):
    return A.creator_profile(ws, f)


@router.get("/insights")
def insights(ws: Workspace = Depends(workspace)):
    return A.insights(ws)


# ---- ML
def _spec(p: PredictIn) -> dict:
    return dict(title=p.title, platform=p.platform, category=p.category, content_type=p.content_type,
                duration_sec=p.duration_sec, publish_at=p.publish_at.isoformat())


@router.get("/ml/model-card")
def model_card(ws: Workspace = Depends(workspace)):
    try:
        return clean(ml.model_card(ws))
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.post("/ml/predict")
def predict(body: PredictIn, ws: Workspace = Depends(workspace)):
    try:
        return clean(ml.predict(ws, _spec(body)))
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.post("/ml/predict/batch")
def predict_batch(body: BatchPredictIn, ws: Workspace = Depends(workspace)):
    try:
        return clean(dict(items=[ml.predict(ws, _spec(p), whatif=False) for p in body.items]))
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.get("/ml/ideas")
def ideas(platform: str | None = Query(None, pattern="^(youtube|instagram|x|linkedin)$"), ws: Workspace = Depends(workspace)):
    try:
        return clean(dict(items=ml.best_ideas(ws, platform, top=6)))
    except ValueError as e:
        raise HTTPException(422, str(e))
