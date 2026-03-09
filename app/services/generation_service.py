"""简历生成服务：基于 JD 与检索上下文生成首版定制简历。"""

from __future__ import annotations

import re
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.adapters.llm_client import get_chat_llm
from app.adapters.vector_store import index_exists, load_vectorstore
from app.core.security import sanitize_jd_text, validate_non_empty
from app.services.session_store import create_session

_RAW_DIR = Path("data/raw")
_TIME_RANGE_PATTERN = re.compile(
    r"(20\d{2}[./-]\d{1,2}\s*(?:[-~至到]\s*(?:20\d{2}[./-]\d{1,2}|今|至今))?)"
)


def _load_prompt_template(file_path: str) -> str:
    return Path(file_path).read_text(encoding="utf-8")


def _load_all_txt_files() -> list[Document]:
    """直接读取 data/raw 下所有 .txt 文件，作为完整上下文。"""
    docs: list[Document] = []
    if not _RAW_DIR.exists():
        return docs
    for txt_path in sorted(_RAW_DIR.rglob("*.txt")):
        if not txt_path.is_file() or txt_path.stat().st_size == 0:
            continue
        content = txt_path.read_text(encoding="utf-8").strip()
        if not content:
            continue
        relative = txt_path.relative_to(_RAW_DIR)
        parts = relative.parts
        category = parts[0] if parts else "未分类"
        entry_folder = parts[1] if len(parts) >= 2 else txt_path.stem
        # 提取条目名称与时间
        match = _TIME_RANGE_PATTERN.search(entry_folder)
        if match:
            period = match.group(1).strip()
            entry_name = entry_folder.replace(period, "", 1).strip(" _-+()（）")
        else:
            entry_name, period = entry_folder, ""
        entry_label = f"{entry_name}（{period}）" if period else entry_name
        docs.append(Document(
            page_content=content,
            metadata={
                "source": str(txt_path),
                "relative_source": str(relative),
                "category": category,
                "entry_key": f"{category}/{entry_folder}",
                "entry_name": entry_name,
                "entry_period": period,
                "entry_label": entry_label,
            },
        ))
    return docs


def _retrieve_non_txt_docs(vectorstore, query: str) -> list[Document]:
    """仅对非 .txt 来源的向量进行检索。"""
    try:
        results = vectorstore.similarity_search(query=query, k=6)
        return [d for d in results if not str(d.metadata.get("source", "")).endswith(".txt")]
    except Exception:
        return []


def _format_retrieved_context(docs: list[Document]) -> str:
    """将召回片段按类别分组格式化，降低 LLM 跨类别混用内容的概率。"""
    from collections import defaultdict

    groups: dict[str, list[tuple[int, Document]]] = defaultdict(list)
    for idx, doc in enumerate(docs, start=1):
        category = doc.metadata.get("category", "未分类")
        groups[category].append((idx, doc))

    # 按固定顺序输出：个人信息 → 技能 → 实习 → 项目 → 其他
    order = ["个人信息", "技能", "实习", "项目"]
    sorted_categories = [c for c in order if c in groups]
    sorted_categories += [c for c in groups if c not in order]

    blocks: list[str] = []
    for category in sorted_categories:
        blocks.append(f"========== 以下为【{category}】类材料 ==========")
        for idx, doc in groups[category]:
            metadata = doc.metadata
            entry_label = metadata.get("entry_label") or metadata.get("entry_name", "未知条目")
            relative_source = metadata.get("relative_source", metadata.get("source", "未知来源"))

            block = (
                f"[证据块{idx}]\n"
                f"类别: {category}\n"
                f"条目: {entry_label}\n"
                f"来源: {relative_source}\n"
                f"内容:\n{doc.page_content.strip()}"
            )
            blocks.append(block)
    return "\n\n".join(blocks)


# ── A4 一页简历长度估算 ───────────────────────
_COMPRESS_PROMPT = """以下是一份 Markdown 格式的简历，请按要求缩减内容。

缩减目标：减少约 {reduce_chars} 个字符（允许误差 ±30 字符，不可缩减过多也不可缩减过少）。
可采取的策略（按优先级）：
- 精简项目/实习描述（去掉冗余字词、压缩句子，每条描述至少保留核心动作+结果）
- 减少技能条目（保留与岗位最相关的）
- 合并相近表述
- 若项目超过3个，可以去掉最不相关的一个（此时可额外减少该项目标题行约15字）

约束：
- 每段实习/项目的描述不得少于40字
- 不得删除任何一级/二级标题
- 不得删除个人信息、教育背景模块的任何一行

直接输出修改后的完整简历，不要解释你的修改。

{resume_text}"""


def compress_resume(resume_text: str, reduce_chars: int = 120) -> str:
    """对外暴露的缩减接口：按指定字符数缩减简历内容。"""
    reduce_chars = max(40, min(reduce_chars, 600))  # 限制范围：40~600字
    llm = get_chat_llm(temperature=0.2)
    chain = ChatPromptTemplate.from_template(_COMPRESS_PROMPT) | llm | StrOutputParser()
    return chain.invoke({"resume_text": resume_text, "reduce_chars": reduce_chars})


def generate_resume(jd_text: str, user_notes: str = "") -> dict:
    """生成首版简历并创建会话。"""
    validate_non_empty(jd_text, "JD文本")
    cleaned_jd = sanitize_jd_text(jd_text)

    # 1. 直接加载所有 .txt 文件作为完整上下文
    txt_docs = _load_all_txt_files()

    # 2. 如果向量索引存在，补充检索非 .txt 来源的文档
    extra_docs: list[Document] = []
    if index_exists():
        vectorstore = load_vectorstore()
        extra_docs = _retrieve_non_txt_docs(vectorstore, cleaned_jd)

    docs = txt_docs + extra_docs
    if not docs:
        raise FileNotFoundError("未找到候选人资料，请检查 data/raw 目录")

    context = _format_retrieved_context(docs)
    sources = sorted({doc.metadata.get("source", "未知来源") for doc in docs})

    prompt = ChatPromptTemplate.from_template(
        _load_prompt_template("app/prompts/generate_resume.md")
    )
    llm = get_chat_llm(temperature=0.4)
    chain = prompt | llm | StrOutputParser()
    resume_text = chain.invoke({"jd_text": cleaned_jd, "context": context, "user_notes": user_notes or "无"})

    session_payload = create_session(cleaned_jd, resume_text, sources)
    first_version = session_payload["versions"][0]
    return {
        "session_id": session_payload["session_id"],
        "version_id": first_version["version_id"],
        "resume_text": first_version["resume_text"],
        "sources": first_version["sources"],
    }


def _prepare_generation(jd_text: str) -> tuple[str, str, list[str]]:
    """准备生成所需的 cleaned_jd、context 和 sources（供流式/非流式复用）。"""
    validate_non_empty(jd_text, "JD文本")
    cleaned_jd = sanitize_jd_text(jd_text)

    txt_docs = _load_all_txt_files()
    extra_docs: list[Document] = []
    if index_exists():
        vectorstore = load_vectorstore()
        extra_docs = _retrieve_non_txt_docs(vectorstore, cleaned_jd)

    docs = txt_docs + extra_docs
    if not docs:
        raise FileNotFoundError("未找到候选人资料，请检查 data/raw 目录")

    context = _format_retrieved_context(docs)
    sources = sorted({doc.metadata.get("source", "未知来源") for doc in docs})
    return cleaned_jd, context, sources


def generate_resume_stream(jd_text: str, user_notes: str = ""):
    """流式生成简历，yield SSE 格式的字符串片段。

    事件类型：
    - data: ... 为正文 token
    - event: done 为结束信号（携带 session_id / version_id）
    - event: error 为错误
    """
    import json

    try:
        cleaned_jd, context, sources = _prepare_generation(jd_text)
    except Exception as exc:
        yield f"event: error\ndata: {json.dumps({'detail': str(exc)}, ensure_ascii=False)}\n\n"
        return

    prompt = ChatPromptTemplate.from_template(
        _load_prompt_template("app/prompts/generate_resume.md")
    )
    llm = get_chat_llm(temperature=0.4)

    # 格式化 prompt 为消息列表
    messages = prompt.format_messages(
        jd_text=cleaned_jd, context=context, user_notes=user_notes or "无"
    )

    # langchain-openai 无法捕获 DeepSeek 的 reasoning_content，改用 openai 原生客户端
    from openai import OpenAI as _OpenAI
    from app.core.config import settings

    client = _OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
    is_reasoner = "reasoner" in settings.deepseek_model.lower()

    # 将 LangChain 消息转为 OpenAI 格式
    oai_messages = []
    for msg in messages:
        role = "user" if msg.type == "human" else ("assistant" if msg.type == "ai" else "system")
        oai_messages.append({"role": role, "content": msg.content})

    stream = client.chat.completions.create(
        model=settings.deepseek_model,
        messages=oai_messages,
        temperature=0 if is_reasoner else 0.4,
        stream=True,
    )

    full_text = ""
    for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if not delta:
            continue

        # DeepSeek R1 的思考过程
        reasoning = getattr(delta, "reasoning_content", None) or ""
        if reasoning:
            escaped = reasoning.replace("\n", "\\n")
            yield f"event: thinking\ndata: {escaped}\n\n"

        content = delta.content or ""
        if content:
            full_text += content
            escaped = content.replace("\n", "\\n")
            yield f"data: {escaped}\n\n"

    # 流结束后保存会话
    session_payload = create_session(cleaned_jd, full_text, sources)
    first_version = session_payload["versions"][0]
    done_data = json.dumps({
        "session_id": session_payload["session_id"],
        "version_id": first_version["version_id"],
    }, ensure_ascii=False)
    yield f"event: done\ndata: {done_data}\n\n"
