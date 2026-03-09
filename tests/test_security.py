"""安全工具单元测试。"""

from app.core.security import sanitize_jd_text


def test_sanitize_jd_text_should_trim_and_limit() -> None:
    """验证 JD 清洗会去空白并限制长度。"""
    raw = "  " + "a" * 13000 + "  "
    cleaned = sanitize_jd_text(raw)
    assert len(cleaned) == 12000
    assert cleaned.startswith("a")
