"""安全辅助模块：输入校验与文本清洗。"""

from __future__ import annotations

import re

MAX_JD_LENGTH = 12000


def sanitize_jd_text(raw_text: str) -> str:
    """清洗 JD 文本并限制长度，降低提示注入风险。"""
    cleaned = raw_text.replace("\x00", " ").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if len(cleaned) > MAX_JD_LENGTH:
        cleaned = cleaned[:MAX_JD_LENGTH]
    return cleaned


def validate_non_empty(text: str, field_name: str) -> None:
    """校验字符串字段不能为空。"""
    if not text or not text.strip():
        raise ValueError(f"{field_name}不能为空")
