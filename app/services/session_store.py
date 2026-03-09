"""会话版本存储：将生成结果保存为本地 JSON，支持回溯。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import settings


def _session_file(session_id: str) -> Path:
    return settings.session_dir / f"{session_id}.json"


def create_session(jd_text: str, resume_text: str, sources: list[str]) -> dict[str, Any]:
    """创建新会话并写入首个版本。"""
    session_id = uuid.uuid4().hex
    version_id = "v1"
    payload = {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "versions": [
            {
                "version_id": version_id,
                "parent_version_id": None,
                "jd_text": jd_text,
                "instruction": "首版生成",
                "resume_text": resume_text,
                "sources": sources,
                "created_at": datetime.now().isoformat(),
            }
        ],
    }
    _session_file(session_id).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def load_session(session_id: str) -> dict[str, Any]:
    """读取指定会话。"""
    file_path = _session_file(session_id)
    if not file_path.exists():
        raise FileNotFoundError("会话不存在，请先生成首版简历")
    return json.loads(file_path.read_text(encoding="utf-8"))


def append_version(
    session_id: str,
    parent_version_id: str,
    jd_text: str,
    instruction: str,
    resume_text: str,
    sources: list[str],
) -> dict[str, Any]:
    """在已有会话中追加新版本。"""
    payload = load_session(session_id)
    next_version = f"v{len(payload['versions']) + 1}"
    payload["versions"].append(
        {
            "version_id": next_version,
            "parent_version_id": parent_version_id,
            "jd_text": jd_text,
            "instruction": instruction,
            "resume_text": resume_text,
            "sources": sources,
            "created_at": datetime.now().isoformat(),
        }
    )
    _session_file(session_id).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def get_version(session_id: str, version_id: str) -> dict[str, Any]:
    """获取会话中的某个版本。"""
    payload = load_session(session_id)
    for version in payload["versions"]:
        if version["version_id"] == version_id:
            return version
    raise ValueError("版本不存在")


def latest_version(session_id: str) -> dict[str, Any]:
    """获取会话最新版本。"""
    payload = load_session(session_id)
    return payload["versions"][-1]
