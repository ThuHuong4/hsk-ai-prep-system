"""Cổng tích hợp AI tập trung của hệ thống Xianglingo."""
from app.integrations.ai.client import (
    AiNotConfiguredError,
    AiProviderError,
    chat_completion,
    get_ai_client,
    json_completion,
    parse_json_reply,
)
from app.integrations.ai.config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    OPENAI_TIMEOUT_SECONDS,
    TTS_VOICE_HOI,
    TTS_VOICE_NAM,
    TTS_VOICE_NU,
    ai_ready,
    current_ai_config,
    image_ready,
    is_real_openai_endpoint,
    stt_ready,
    tts_ready,
    vision_ready,
)
from app.integrations.ai.media import PCM_RATE, image_bytes, look_at_image, speech_pcm, transcribe
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
    "PCM_RATE",
    "TTS_VOICE_HOI",
    "TTS_VOICE_NAM",
    "TTS_VOICE_NU",
    "ai_ready",
    "image_bytes",
    "image_ready",
    "look_at_image",
    "stt_ready",
    "transcribe",
    "vision_ready",
    "speech_pcm",
    "tts_ready",
    "chat_completion",
    "get_ai_client",
    "json_completion",
]
