"""YouTube trending-video engagement analysis (clustering). Descriptive, built on historical Kaggle data."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.models.tables import User
from app.security.auth import current_user
from app.services import trending

router = APIRouter(prefix="/api/research", tags=["research"])


@router.get("/trending/countries")
def countries(_: User = Depends(current_user)):
    return dict(items=trending.countries())


@router.get("/trending/{country}")
def trending_clusters(country: str, _: User = Depends(current_user)):
    try:
        res = trending.get(country)
    except Exception as exc:  # noqa: BLE001 - surface a clear message instead of a stack trace
        raise HTTPException(422, f"Could not analyse the dataset: {exc}") from exc
    if res is None:
        raise HTTPException(404, "No trending dataset for that country. Add its CSV to backend/data/kaggle_youtube/ (see docs/TRENDING_ANALYSIS.md).")
    return res
