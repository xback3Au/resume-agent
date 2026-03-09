"""向量库适配：封装 Chroma 的创建与加载。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import settings


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    """懒加载本地向量化模型。"""
    return HuggingFaceEmbeddings(model_name=settings.embedding_model)


def load_vectorstore() -> Chroma:
    """加载本地持久化 Chroma 索引。"""
    return Chroma(
        collection_name=settings.collection_name,
        embedding_function=get_embeddings(),
        persist_directory=str(settings.index_dir),
    )


def index_exists() -> bool:
    """检测索引目录是否已有内容。"""
    index_path = Path(settings.index_dir)
    if not index_path.exists():
        return False
    return any(index_path.iterdir())
