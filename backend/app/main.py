from __future__ import annotations

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import assistant, auth, connect, data, privacy, research
from app.config import get_settings
from app.db import init_db


def _warm_demo_model() -> None:
    try:
        from app.ml import pipeline as ml
        from app.services.dataset import demo_workspace
        ws = demo_workspace()
        ml.get_bundle(ws)
        from app.services import analytics as A
        A.insights(ws); A.cross_platform(ws, None); A.detect_anomalies(ws, None); A.best_publish_times(ws, None)
    except Exception as exc:  # warm-up is best effort; requests will train lazily and surface real errors
        print(f"[socialiq] demo model warm-up failed: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    threading.Thread(target=_warm_demo_model, daemon=True).start()
    yield


settings = get_settings()
app = FastAPI(title="SocialIQ API", version="0.1.0", lifespan=lifespan,
              docs_url=None if settings.is_production else "/docs", redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False,
                   allow_methods=["GET", "POST", "DELETE"], allow_headers=["Authorization", "Content-Type"])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
                         "Cache-Control": "no-store"})
    if settings.is_production:
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return resp


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    print(f"[socialiq] unhandled error on {request.url.path}: {type(exc).__name__}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on our side. Please try again."})


for r in (auth.router, connect.router, data.router, assistant.router, privacy.router, research.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {"status": "ok", "llm_configured": bool(settings.gemini_api_key), "llm_provider": "gemini" if settings.gemini_api_key else None}


# Single-container deployment: serve the built SPA when present (frontend/dist or /app/static).
from pathlib import Path  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402

_STATIC = next((p for p in (Path(__file__).resolve().parents[1] / "static", Path(__file__).resolve().parents[2] / "frontend" / "dist") if (p / "index.html").exists()), None)
if _STATIC is not None:
    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        f = (_STATIC / path).resolve()
        if path and f.is_file() and _STATIC.resolve() in f.parents:
            return FileResponse(f)
        return FileResponse(_STATIC / "index.html")
