"""OCR 路由：接收图片并使用千问视觉模型提取文字。"""

from __future__ import annotations

import base64

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.adapters.llm_client import get_vision_llm

router = APIRouter()

# 允许的图片 MIME 类型
_ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp", "image/gif", "image/bmp"}
# 最大 base64 数据长度（约 10MB 原始图片）
_MAX_B64_LEN = 15_000_000


class OcrRequest(BaseModel):
    """图片 OCR 请求体。"""

    image_b64: str
    mime_type: str = "image/png"


@router.post("/ocr-jd")
def ocr_jd(request: OcrRequest) -> dict:
    """从 JD 截图中提取文字。"""
    if request.mime_type not in _ALLOWED_MIME:
        raise HTTPException(status_code=400, detail=f"不支持的图片类型: {request.mime_type}")
    if len(request.image_b64) > _MAX_B64_LEN:
        raise HTTPException(status_code=400, detail="图片过大，请压缩后重试")

    # 验证 base64 合法性
    try:
        base64.b64decode(request.image_b64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="无效的 base64 图片数据")

    data_url = f"data:{request.mime_type};base64,{request.image_b64}"

    try:
        llm = get_vision_llm()
        from langchain_core.messages import HumanMessage

        message = HumanMessage(
            content=[
                {"type": "image_url", "image_url": {"url": data_url}},
                {
                    "type": "text",
                    "text": (
                        "请完整提取这张图片中的所有文字内容，保持原始格式和换行。"
                        "只输出提取到的文字，不要添加任何解释或说明。"
                    ),
                },
            ]
        )
        result = llm.invoke([message])
        return {"text": result.content.strip()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"图片文字提取失败: {exc}") from exc
