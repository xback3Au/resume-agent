"""FastAPI 应用入口：注册路由并托管本地网页。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes_export import router as export_router
from app.api.routes_generate import router as generate_router
from app.api.routes_ocr import router as ocr_router
from app.api.routes_rewrite import router as rewrite_router
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(title="简历定制智能体", version="0.1.0")
app.include_router(generate_router, prefix="/api", tags=["generate"])
app.include_router(rewrite_router, prefix="/api", tags=["rewrite"])
app.include_router(export_router, prefix="/api", tags=["export"])
app.include_router(ocr_router, prefix="/api", tags=["ocr"])

web_dir = Path("web")
if web_dir.exists():
    app.mount("/web", StaticFiles(directory=str(web_dir)), name="web")


@app.get("/")
def index() -> FileResponse:
    """返回本地前端页面。"""
    return FileResponse("web/index.html")


@app.get("/health")
def health() -> dict[str, str]:
    """健康检查接口。"""
    return {"status": "ok"}
