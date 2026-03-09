"""LLM 客户端适配：DeepSeek 文本生成 + 千问视觉 OCR。"""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.core.config import settings


def get_chat_llm(temperature: float = 0.2) -> ChatOpenAI:
    """创建 DeepSeek 对话模型客户端。"""
    if not settings.deepseek_api_key:
        raise ValueError("未检测到DEEPSEEK_API_KEY，请先在.env中配置")

    # deepseek-reasoner (R1) 不支持 temperature 参数
    is_reasoner = "reasoner" in settings.deepseek_model.lower()

    return ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0 if is_reasoner else temperature,
    )


def get_vision_llm(temperature: float = 0.0) -> ChatOpenAI:
    """创建通义千问视觉模型客户端（用于图片文字提取）。"""
    if not settings.qwen_api_key:
        raise ValueError("未检测到QWEN_API_KEY，请先在.env中配置")

    return ChatOpenAI(
        model=settings.qwen_vl_model,
        api_key=settings.qwen_api_key,
        base_url=settings.qwen_base_url,
        temperature=temperature,
    )
