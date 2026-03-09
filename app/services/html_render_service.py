"""HTML 渲染服务：Markdown 简历文本 → 带样式的 HTML 页面。"""

from __future__ import annotations

import base64
import re
from pathlib import Path

import markdown

_PHOTO_PATH = Path("data/uploads/me.jpg")

# CSS 模板路径
_CSS_PATH = Path(__file__).resolve().parent.parent / "templates" / "resume_a4.css"


def _load_css() -> str:
    """读取 CSS 模板文件。"""
    return _CSS_PATH.read_text(encoding="utf-8")


def _estimate_density(md_text: str) -> str:
    """根据内容长度估算排版密度，返回 CSS class。"""
    lines = [l for l in md_text.strip().splitlines() if l.strip()]
    if len(lines) < 18:
        return "spacious"
    if len(lines) > 38:
        return "compact"
    return ""


def _preprocess_markdown(md_text: str) -> str:
    """预处理 Markdown，确保经历条目标题用 ### 表示。

    识别「公司/项目名 · 职位 · 时间」格式的加粗行，
    将其转为 ### 三级标题以触发 CSS 中的条目标题样式。
    """
    lines = md_text.splitlines()
    result = []
    in_experience = False
    experience_keywords = {"实习经历", "项目经历", "工作经历", "科研经历", "竞赛经历"}

    for line in lines:
        stripped = line.strip()

        # 检测是否进入经历类板块
        heading_match = re.match(r"^\s*##\s*\**\s*(.+?)\s*\**\s*$", stripped)
        if heading_match:
            section_name = heading_match.group(1).strip()
            in_experience = any(kw in section_name for kw in experience_keywords)
            result.append(line)
            continue

        # 在经历板块中，识别条目标题行
        if in_experience and stripped:
            # 匹配经历条目标题：含 · 的行，或 **标题** *时间* 格式
            is_title = (
                re.match(r"^\*\*.+·.+\*\*", stripped)
                or re.match(r"^.+·.+·.+$", stripped)
                or (re.match(r"^\*\*.+\*\*", stripped) and "·" in stripped)
                or re.match(r"^\*\*.+\*\*\s+\*.+\*\s*$", stripped)
                or ("·" in stripped and bool(re.search(r"\*\d{4}", stripped)))  # 项目名 · *20xx...（单·无职位）
            )
            if is_title:
                # 提取末尾斜体时间（要求前面有空格，内容不含 *，避免匹配到 ** 加粗）
                time_match = re.search(r"\s+\*([^*]+)\*\s*$", stripped)
                if time_match:
                    time_str = time_match.group(1)
                    # 去掉末尾可能残留的 ·
                    prefix = stripped[: time_match.start()].rstrip().rstrip("·").rstrip()
                    # 去掉 prefix 外层的 **...**
                    prefix = re.sub(r"^\*\*(.+)\*\*$", r"\1", prefix)
                    result.append(f"### {prefix} *{time_str}*")
                else:
                    clean = re.sub(r"^\*\*(.+)\*\*$", r"\1", stripped)
                    result.append(f"### {clean}")
                continue

        result.append(line)

    return "\n".join(result)


def render_html(resume_text: str, compact: bool = False) -> str:
    """将 Markdown 简历文本渲染为完整的 HTML 页面。

    Parameters
    ----------
    resume_text : str
        Markdown 格式的简历文本。
    compact : bool
        是否强制紧凑模式。

    Returns
    -------
    str
        完整的 HTML 文档字符串。
    """
    css = _load_css()
    processed = _preprocess_markdown(resume_text)

    # 自动判断密度
    if compact:
        density_class = "compact"
    else:
        density_class = _estimate_density(resume_text)

    # 渲染 Markdown → HTML
    html_body = markdown.markdown(
        processed,
        extensions=["tables", "sane_lists", "nl2br"],
        output_format="html5",
    )

    # 如果存在照片，始终插入到 html_body 最前面（float:right 自然与第一行内容顶部对齐）
    if _PHOTO_PATH.exists():
        photo_b64 = base64.b64encode(_PHOTO_PATH.read_bytes()).decode("ascii")
        photo_tag = f'<img class="resume-photo" src="data:image/jpeg;base64,{photo_b64}" alt="照片">'
        html_body = photo_tag + "\n" + html_body

    page = f"""\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>简历</title>
<style>
{css}
</style>
</head>
<body>
<div class="resume-page {density_class}">
{html_body}
</div>
</body>
</html>"""
    return page
