"""日志配置模块：默认控制台输出并执行敏感信息脱敏。"""

from __future__ import annotations

import logging
import re


class MaskSecretsFilter(logging.Filter):
    """对日志中的常见密钥与敏感字段做脱敏。"""

    patterns = [
        re.compile(r"(sk-[A-Za-z0-9]{8,})"),
        re.compile(r"(DEEPSEEK_API_KEY\s*=\s*)([^\s]+)", re.IGNORECASE),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        message = str(record.getMessage())
        for pattern in self.patterns:
            message = pattern.sub(r"\1***", message)
        record.msg = message
        record.args = ()
        return True


def setup_logging() -> None:
    """初始化日志系统。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    root_logger = logging.getLogger()
    root_logger.addFilter(MaskSecretsFilter())
