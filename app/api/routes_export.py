"""导出路由：下载简历文件（TXT/DOCX/PDF）、模板管理、预览。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from app.core.config import settings
from app.services.export_service import (
    IMAGE_SUFFIXES,
    SUPPORTED_EXPORT_FORMATS,
    export_docx,
    export_pdf,
    export_txt,
    list_templates,
    render_docx_from_text,
)
from app.services.html_render_service import render_html
from app.services.pdf_render_service import render_pdf_from_text

router = APIRouter()


# ── 模板列表 ──────────────────────────────────────


@router.get("/templates")
def get_templates() -> list[dict[str, str]]:
    """列出可用的 DOCX 模板。"""
    return list_templates()


# ── 照片上传 ──────────────────────────────────────


@router.post("/upload-photo")
async def upload_photo(file: UploadFile = File(...)) -> dict:
    """上传照片文件到 data/uploads。"""
    if not file.filename:
        raise HTTPException(400, "文件名不能为空")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in IMAGE_SUFFIXES:
        raise HTTPException(400, f"仅支持图片文件（{', '.join(IMAGE_SUFFIXES)}）")
    dest = settings.upload_dir / Path(file.filename).name
    content = await file.read()
    dest.write_bytes(content)
    return {"filename": dest.name}


# ── DOCX 预览 ─────────────────────────────────────


class PreviewRequest(BaseModel):
    """预览请求体。"""

    resume_text: str
    template: str | None = None
    photo_file: str | None = None
    compact: bool = False


@router.post("/preview-docx")
def preview_docx(request: PreviewRequest) -> Response:
    """接收简历文本，返回 DOCX 字节流（用于前端预览/下载）。"""
    try:
        content = render_docx_from_text(
            resume_text=request.resume_text,
            template_name=request.template,
            photo_filename=request.photo_file,
            compact=request.compact,
        )
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    except Exception as exc:
        raise HTTPException(400, detail=str(exc)) from exc


@router.post("/preview-html")
def preview_html(request: PreviewRequest) -> Response:
    """接收简历文本，返回渲染好的 HTML 页面（用于前端 iframe 预览 / 浏览器端 PDF 导出）。"""
    try:
        html = render_html(
            resume_text=request.resume_text,
            compact=request.compact,
        )
        return Response(content=html, media_type="text/html; charset=utf-8")
    except Exception as exc:
        raise HTTPException(400, detail=str(exc)) from exc


@router.post("/render-pdf")
def render_pdf(request: PreviewRequest) -> Response:
    """接收简历文本，使用 Playwright 渲染为 PDF 并返回字节流（一键下载）。"""
    try:
        pdf_bytes = render_pdf_from_text(
            resume_text=request.resume_text,
            compact=request.compact,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=resume.pdf"},
        )
    except Exception as exc:
        raise HTTPException(400, detail=str(exc)) from exc


# ── 文件导出 ──────────────────────────────────────


@router.get("/export")
def export_resume(
    session_id: str = Query(..., description="会话ID"),
    version_id: str = Query(..., description="版本ID"),
    export_format: str = Query("txt", alias="format", description="导出格式：txt/docx/pdf"),
    photo_file: str | None = Query(None, description="照片文件名"),
    template: str | None = Query(None, description="模板文件名"),
) -> FileResponse:
    """导出并下载简历文件。"""
    try:
        fmt = export_format.lower().strip()
        if fmt not in SUPPORTED_EXPORT_FORMATS:
            raise ValueError(f"不支持的导出格式: {export_format}")

        if fmt == "txt":
            file_path = export_txt(session_id=session_id, version_id=version_id)
            media_type = "text/plain"
        elif fmt == "docx":
            file_path = export_docx(
                session_id=session_id,
                version_id=version_id,
                photo_filename=photo_file,
                template_name=template,
            )
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            file_path = export_pdf(
                session_id=session_id,
                version_id=version_id,
                photo_filename=photo_file,
                template_name=template,
            )
            media_type = "application/pdf"

        return FileResponse(path=file_path, media_type=media_type, filename=file_path.name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
