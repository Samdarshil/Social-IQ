from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import rate_limit, workspace
from app.schemas.api import ChatIn
from app.services import assistant
from app.services.analytics import clean
from app.services.assistant_tools import TOOL_SCHEMAS
from app.services.dataset import Workspace

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/chat", dependencies=[Depends(rate_limit(30, 60))])
def chat(body: ChatIn, ws: Workspace = Depends(workspace)):
    out = assistant.chat(ws, body.message, [t.model_dump() for t in body.history])
    out["source"] = ws.source.model_dump()
    return clean(out)


@router.get("/tools")
def tools():
    return [dict(name=t["name"], description=t["description"]) for t in TOOL_SCHEMAS]
