"""PDF 导出服务：使用 Playwright + 本地 Chrome 将 HTML 渲染为 PDF。"""

from __future__ import annotations

import asyncio
import os

from app.services.html_render_service import render_html


def _find_local_chrome() -> str | None:
    """尝试找到本地安装的 Chrome 或 Edge 可执行文件路径。"""
    candidates = [
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


async def _render_pdf_async(html: str) -> bytes:
    """异步：启动无头浏览器，将 HTML 渲染为 A4 PDF 并返回字节。"""
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        # 优先使用本地 Chrome/Edge（避免下载 playwright 自带浏览器）
        local_chrome = _find_local_chrome()
        if local_chrome:
            browser = await pw.chromium.launch(executable_path=local_chrome)
        else:
            browser = await pw.chromium.launch(channel="chrome")
        page = await browser.new_page()
        await page.set_content(html, wait_until="networkidle")
        pdf_bytes = await page.pdf(
            format="A4",
            margin={"top": "14mm", "right": "16mm", "bottom": "12mm", "left": "16mm"},
            print_background=True,
        )
        await browser.close()
    return pdf_bytes


def render_pdf_from_text(
    resume_text: str,
    compact: bool = False,
) -> bytes:
    """将 Markdown 简历文本渲染为 PDF 字节。

    Parameters
    ----------
    resume_text : str
        Markdown 格式的简历文本。
    compact : bool
        是否使用紧凑排版。

    Returns
    -------
    bytes
        PDF 文件的二进制内容。
    """
    html = render_html(resume_text, compact=compact)
    # 在同步上下文中运行异步函数
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # 已在事件循环中（如 FastAPI），使用新线程
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            pdf_bytes = pool.submit(
                lambda: asyncio.run(_render_pdf_async(html))
            ).result()
    else:
        pdf_bytes = asyncio.run(_render_pdf_async(html))

    return pdf_bytes
