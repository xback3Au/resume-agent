"""改写路由：根据指令改写指定版本简历。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.rewrite_service import rewrite_resume
from app.services.session_store import get_version

router = APIRouter()


class RewriteRequest(BaseModel):
    """改写请求体。"""

    session_id: str
    version_id: str
    instruction: str


@router.post("/rewrite")
def rewrite(request: RewriteRequest) -> dict:
    """对已有简历版本进行迭代改写。"""
    try:
        return rewrite_resume(
            session_id=request.session_id,
            version_id=request.version_id,
            instruction=request.instruction,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/version")
def fetch_version(session_id: str, version_id: str) -> dict:
    """获取指定版本内容（用于前端回退查看）。"""
    try:
        version = get_version(session_id, version_id)
        return {
            "session_id": session_id,
            "version_id": version["version_id"],
            "parent_version_id": version.get("parent_version_id"),
            "resume_text": version.get("resume_text", ""),
            "instruction": version.get("instruction", ""),
            "sources": version.get("sources", []),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
