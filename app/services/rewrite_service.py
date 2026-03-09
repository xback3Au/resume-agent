"""简历改写服务：基于上一版本与用户指令生成新版本。"""

from __future__ import annotations

from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.adapters.llm_client import get_chat_llm
from app.core.security import validate_non_empty
from app.services.session_store import append_version, get_version


def _load_prompt_template(file_path: str) -> str:
    return Path(file_path).read_text(encoding="utf-8")


def rewrite_resume(session_id: str, version_id: str, instruction: str) -> dict:
    """按用户指令改写简历并生成新版本。"""
    validate_non_empty(instruction, "改写指令")
    target_version = get_version(session_id, version_id)

    prompt = ChatPromptTemplate.from_template(
        _load_prompt_template("app/prompts/rewrite_resume.md")
    )
    llm = get_chat_llm(temperature=0.4)
    chain = prompt | llm | StrOutputParser()

    new_resume = chain.invoke(
        {
            "instruction": instruction.strip(),
            "previous_resume": target_version["resume_text"],
            "jd_text": target_version["jd_text"],
        }
    )

    payload = append_version(
        session_id=session_id,
        parent_version_id=version_id,
        jd_text=target_version["jd_text"],
        instruction=instruction.strip(),
        resume_text=new_resume,
        sources=target_version.get("sources", []),
    )
    latest = payload["versions"][-1]
    return {
        "session_id": session_id,
        "version_id": latest["version_id"],
        "resume_text": latest["resume_text"],
        "sources": latest["sources"],
    }
