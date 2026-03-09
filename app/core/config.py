"""项目配置模块：统一读取环境变量与默认值。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """应用配置对象。"""

    # DeepSeek 文本生成
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")
    # 千问视觉模型（OCR）
    qwen_api_key: str = os.getenv("QWEN_API_KEY", "")
    qwen_base_url: str = os.getenv(
        "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    qwen_vl_model: str = os.getenv("QWEN_VL_MODEL", "qwen-vl-plus")
    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    index_dir: Path = Path(os.getenv("INDEX_DIR", "data/index"))
    session_dir: Path = Path(os.getenv("SESSION_DIR", "data/sessions"))
    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", "data/uploads"))
    template_dir: Path = Path(os.getenv("TEMPLATE_DIR", "data/templates"))
    collection_name: str = os.getenv("COLLECTION_NAME", "resume_memory")

    def ensure_dirs(self) -> None:
        """确保项目运行所需目录存在。"""
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.template_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
