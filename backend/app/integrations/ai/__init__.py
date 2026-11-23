"""Cổng tích hợp AI tập trung của hệ thống Xianglingo."""
from app.integrations.ai.client import (
    AiNotConfiguredError,
    AiProviderError,
    chat_completion,
    get_ai_client,
    json_completion,
)
from app.integrations.ai.config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    OPENAI_TIMEOUT_SECONDS,
    ai_ready,
)
from app.integrations.ai.prompts import XIANG_JSON_SYSTEM_PROMPT, XIANG_POST_CHECK_SYSTEM_PROMPT

__all__ = [
    "AiNotConfiguredError",
    "AiProviderError",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "OPENAI_TIMEOUT_SECONDS",
    "XIANG_JSON_SYSTEM_PROMPT",
    "XIANG_POST_CHECK_SYSTEM_PROMPT",
    "ai_ready",
    "chat_completion",
    "get_ai_client",
    "json_completion",
]
