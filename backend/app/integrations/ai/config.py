"""Cấu hình môi trường cho nhà cung cấp AI (hỗ trợ mặc định AI miễn phí cho Văn bản, Giọng đọc và Hình ảnh).

- Văn bản / Chấm viết / Soạn đề / Trợ giảng: Google Gemini miễn phí (Google AI Studio), Groq miễn phí, OpenRouter hoặc OpenAI.
- Giọng đọc tiếng Trung (TTS): Mặc định dùng Microsoft Edge Neural TTS (`edge-tts`) miễn phí 100%, không cần API key, đủ 3 giọng Nam / Nữ / Phát thanh viên chuẩn phổ thông.
- Tạo hình minh họa đề HSK: Mặc định dùng Pollinations Flux miễn phí 100% (không cần API key), có thể gắn thêm `HF_API_KEY` (HuggingFace miễn phí) hoặc `OPENAI_IMAGE_MODEL` nếu dùng OpenAI thật.
- Tự động nạp lại `.env` khi tệp thay đổi để Giảng viên / Quản trị đổi khóa API không cần khởi động lại máy chủ.
"""
import importlib.util
import os
import threading
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

BASE_DIR = Path(__file__).resolve().parents[3]  # d:\HSK_AI\backend
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

_env_lock = threading.Lock()
_env_mtime: float | None = None
_file_cfg: dict[str, str] = {}

OPENAI_TIMEOUT_SECONDS = 60
MEDIA_TIMEOUT_SECONDS = 120

# Giọng tiếng Trung chuẩn phổ thông (miễn phí qua edge-tts)
DEFAULT_EDGE_VOICE_NAM = "zh-CN-YunxiNeural"
DEFAULT_EDGE_VOICE_NU = "zh-CN-XiaoxiaoNeural"
DEFAULT_EDGE_VOICE_HOI = "zh-CN-YunjianNeural"


def _refresh_env() -> dict[str, str]:
    """Đọc lại `.env` nếu thời điểm sửa tệp thay đổi (không ghi đè biến môi trường tiến trình như khi chạy test)."""
    global _env_mtime, _file_cfg
    try:
        mtime = ENV_FILE.stat().st_mtime if ENV_FILE.is_file() else None
    except OSError:
        mtime = None
    if mtime != _env_mtime:
        with _env_lock:
            if mtime != _env_mtime:
                raw = dotenv_values(ENV_FILE) if mtime is not None else {}
                _file_cfg = {k: (v or "").strip() for k, v in raw.items() if k}
                _env_mtime = mtime
    return _file_cfg


def get_env(name: str, default: str = "") -> str:
    """Ưu tiên biến môi trường hệ thống (nếu khác giá trị nạp lúc đầu) hoặc giá trị mới nhất trong `.env`."""
    file_vals = _refresh_env()
    if name in file_vals:
        return file_vals[name]
    return os.getenv(name, default).strip()


# Giữ các hằng mức module để tương thích ngược với code import trực tiếp
OPENAI_API_KEY = get_env("OPENAI_API_KEY")
OPENAI_MODEL = get_env("OPENAI_MODEL")
OPENAI_BASE_URL = get_env("OPENAI_BASE_URL") or None
OPENAI_TTS_MODEL = get_env("OPENAI_TTS_MODEL")
OPENAI_IMAGE_MODEL = get_env("OPENAI_IMAGE_MODEL")
OPENAI_IMAGE_QUALITY = get_env("OPENAI_IMAGE_QUALITY") or "low"
TTS_VOICE_NAM = get_env("OPENAI_TTS_VOICE_NAM") or "nam"
TTS_VOICE_NU = get_env("OPENAI_TTS_VOICE_NU") or "nu"
TTS_VOICE_HOI = get_env("OPENAI_TTS_VOICE_HOI") or "hoi"
OPENAI_VISION_MODEL = get_env("OPENAI_VISION_MODEL")
OPENAI_STT_MODEL = get_env("OPENAI_STT_MODEL")


def current_ai_config() -> dict[str, str | None]:
    """Trả cấu hình AI hiện hành (luôn cập nhật mới nhất theo `.env`)."""
    api_key = get_env("OPENAI_API_KEY") or get_env("GEMINI_API_KEY") or get_env("GROQ_API_KEY")
    base_url = get_env("OPENAI_BASE_URL") or None
    model = get_env("OPENAI_MODEL")
    if not base_url and api_key.startswith("AIza"):
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        model = model or "gemini-2.5-flash"
    elif not base_url and api_key.startswith("gsk_"):
        base_url = "https://api.groq.com/openai/v1"
        model = model or "llama-3.3-70b-versatile"
    return {
        "api_key": api_key,
        "model": model,
        "base_url": base_url,
        "tts_provider": get_env("TTS_PROVIDER").lower(),
        "tts_model": get_env("OPENAI_TTS_MODEL"),
        "image_provider": get_env("IMAGE_PROVIDER").lower(),
        "image_model": get_env("OPENAI_IMAGE_MODEL"),
        "image_quality": get_env("OPENAI_IMAGE_QUALITY") or "low",
        "hf_api_key": get_env("HF_API_KEY"),
        "vision_model": get_env("OPENAI_VISION_MODEL"),
        "stt_model": get_env("OPENAI_STT_MODEL"),
        "edge_voice_nam": get_env("EDGE_TTS_VOICE_NAM") or DEFAULT_EDGE_VOICE_NAM,
        "edge_voice_nu": get_env("EDGE_TTS_VOICE_NU") or DEFAULT_EDGE_VOICE_NU,
        "edge_voice_hoi": get_env("EDGE_TTS_VOICE_HOI") or DEFAULT_EDGE_VOICE_HOI,
    }


def is_gemini_endpoint(base_url: str | None = None) -> bool:
    url = (base_url if base_url is not None else (current_ai_config()["base_url"] or "")).lower()
    return "generativelanguage.googleapis.com" in url


def is_groq_endpoint(base_url: str | None = None) -> bool:
    url = (base_url if base_url is not None else (current_ai_config()["base_url"] or "")).lower()
    return "api.groq.com" in url


def is_real_openai_endpoint(base_url: str | None = None) -> bool:
    url = (base_url if base_url is not None else (current_ai_config()["base_url"] or "")).lower()
    return not url or "api.openai.com" in url


def edge_tts_available() -> bool:
    return bool(importlib.util.find_spec("edge_tts") and importlib.util.find_spec("miniaudio"))


def resolve_vision_model() -> str:
    """Chọn model nhìn ảnh phù hợp với nhà cung cấp hiện tại (Gemini hỗ trợ nhìn ảnh ngay trên model chính)."""
    cfg = current_ai_config()
    if not cfg["api_key"]:
        return ""
    explicit = cfg["vision_model"] or ""
    if is_gemini_endpoint(cfg["base_url"]):
        if explicit and not explicit.startswith("gpt-"):
            return explicit
        return cfg["model"] or ""
    if is_groq_endpoint(cfg["base_url"]):
        if explicit and not explicit.startswith("gpt-"):
            return explicit
        return ""
    return explicit


def resolve_stt_mode() -> tuple[str, str]:
    """Trả `(che_do, ten_model)`: `'gemini_chat'`, `'openai_whisper'` hoặc `('', '')`."""
    cfg = current_ai_config()
    if not cfg["api_key"]:
        return ("", "")
    explicit = cfg["stt_model"] or ""
    if is_gemini_endpoint(cfg["base_url"]):
        model = explicit if (explicit and not explicit.startswith("gpt-")) else (cfg["model"] or "")
        return ("gemini_chat", model) if model else ("", "")
    if is_groq_endpoint(cfg["base_url"]):
        model = explicit if (explicit and not explicit.startswith("gpt-")) else "whisper-large-v3-turbo"
        return ("openai_whisper", model)
    if explicit:
        return ("openai_whisper", explicit)
    return ("", "")


def ai_ready() -> bool:
    """Kiểm tra hệ thống đã khai báo đủ khóa API và tên mô hình AI văn bản chưa."""
    cfg = current_ai_config()
    return bool(cfg["api_key"] and cfg["model"])


def tts_ready() -> bool:
    """Giọng đọc tiếng Trung luôn sẵn sàng khi có `edge-tts` miễn phí hoặc cấu hình OpenAI TTS thật."""
    if edge_tts_available():
        return True
    cfg = current_ai_config()
    return bool(cfg["api_key"] and cfg["tts_model"] and is_real_openai_endpoint(cfg["base_url"]))


def image_ready() -> bool:
    """Tạo hình minh họa luôn sẵn sàng nhờ cổng Pollinations Flux miễn phí (kèm HuggingFace / OpenAI nếu có)."""
    return True


def vision_ready() -> bool:
    return bool(resolve_vision_model())


def stt_ready() -> bool:
    mode, model = resolve_stt_mode()
    return bool(mode and model)
