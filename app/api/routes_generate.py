"""生成路由：接收 JD 文本并返回首版简历。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.generation_service import generate_resume, generate_resume_stream, compress_resume

router = APIRouter()


class GenerateRequest(BaseModel):
    """首版生成请求体。"""

    jd_text: str
    user_notes: str = ""


class CompressRequest(BaseModel):
    """缩减请求体。"""

    resume_text: str
    reduce_chars: int = 0


@router.post("/generate")
def generate(request: GenerateRequest) -> dict:
    """根据 JD 生成首版简历。"""
    try:
        return generate_resume(request.jd_text, request.user_notes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/generate-stream")
def generate_stream(request: GenerateRequest):
    """流式生成首版简历（SSE）。"""
    return StreamingResponse(
        generate_resume_stream(request.jd_text, request.user_notes),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/compress")
def compress(request: CompressRequest) -> dict:
    """缩减简历内容。"""
    try:
        result = compress_resume(request.resume_text, request.reduce_chars)
        return {"resume_text": result}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
