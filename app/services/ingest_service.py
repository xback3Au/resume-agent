"""文档入库服务：读取私有资料并构建向量索引。"""

from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.adapters.vector_store import get_embeddings
from app.core.config import settings

SUPPORTED_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}
TIME_RANGE_PATTERN = re.compile(
    r"(20\d{2}[./-]\d{1,2}\s*(?:[-~至到]\s*(?:20\d{2}[./-]\d{1,2}|今|至今))?)"
)


def _is_office_temp_file(file_path: Path) -> bool:
    """识别 Office 产生的临时锁文件（如 ~$xxx.docx）。"""
    return file_path.suffix.lower() == ".docx" and file_path.name.startswith("~$")


def _load_single_file(file_path: Path) -> list[Document]:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return PyPDFLoader(str(file_path)).load()
    if suffix == ".docx":
        return Docx2txtLoader(str(file_path)).load()
    return TextLoader(str(file_path), encoding="utf-8").load()


def _extract_name_and_period(raw_name: str) -> tuple[str, str]:
    """从目录名中提取条目名称与时间范围。"""
    cleaned = raw_name.strip()
    match = TIME_RANGE_PATTERN.search(cleaned)
    if not match:
        return cleaned, ""

    period = match.group(1).strip()
    name = cleaned.replace(period, "", 1).strip(" _-+()（）")
    return (name or cleaned), period


def _build_document_metadata(input_dir: Path, file_path: Path) -> dict[str, str]:
    """基于 data/raw 目录结构构建条目级元数据。"""
    relative = file_path.relative_to(input_dir)
    parts = relative.parts

    category = parts[0] if parts else "未分类"
    entry_folder = parts[1] if len(parts) >= 2 else file_path.stem
    entry_name, entry_period = _extract_name_and_period(entry_folder)

    # 用 category + entry_folder 作为稳定条目标识，便于后续在生成阶段绑定证据。
    entry_key = f"{category}/{entry_folder}"
    entry_label = f"{entry_name}（{entry_period}）" if entry_period else entry_name

    return {
        "source": str(file_path),
        "relative_source": str(relative),
        "category": category,
        "entry_key": entry_key,
        "entry_name": entry_name,
        "entry_period": entry_period,
        "entry_label": entry_label,
    }


def load_documents(input_dir: Path) -> list[Document]:
    """遍历目录并加载支持格式的文档。"""
    documents: list[Document] = []
    for file_path in input_dir.rglob("*"):
        if (
            not file_path.is_file()
            or file_path.suffix.lower() not in SUPPORTED_SUFFIXES
            or _is_office_temp_file(file_path)
        ):
            continue
        loaded_docs = _load_single_file(file_path)
        metadata = _build_document_metadata(input_dir, file_path)
        for doc in loaded_docs:
            doc.metadata.update(metadata)
            documents.append(doc)
    return documents


def split_documents(documents: list[Document]) -> list[Document]:
    """执行中文友好的文本切分。"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=80,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    deduplicated: list[Document] = []
    seen_hashes: set[str] = set()

    for chunk in chunks:
        normalized = " ".join(chunk.page_content.split())
        chunk_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        if chunk_hash in seen_hashes:
            continue
        seen_hashes.add(chunk_hash)
        chunk.metadata["chunk_hash"] = chunk_hash
        deduplicated.append(chunk)
    return deduplicated


def build_or_replace_index(chunks: list[Document]) -> int:
    """重建 Chroma 索引。"""
    if settings.index_dir.exists():
        shutil.rmtree(settings.index_dir)
    settings.index_dir.mkdir(parents=True, exist_ok=True)

    Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        collection_name=settings.collection_name,
        persist_directory=str(settings.index_dir),
    )
    return len(chunks)


def ingest_documents(input_dir: str) -> dict[str, int]:
    """对外入口：执行文档加载、切分与索引构建。"""
    input_path = Path(input_dir)
    if not input_path.exists():
        raise FileNotFoundError("输入目录不存在")

    docs = load_documents(input_path)
    if not docs:
        raise ValueError("未找到可入库文档，请检查目录与文件格式")

    chunks = split_documents(docs)
    chunk_count = build_or_replace_index(chunks)
    return {"document_count": len(docs), "chunk_count": chunk_count}
