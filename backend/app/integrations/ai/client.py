"""Cổng gọi mô hình AI tập trung (Singleton OpenAI client, xử lý lỗi và bóc JSON thống nhất).

Quy tắc bắt buộc toàn dự án:
- Luôn đóng/rollback giao dịch CSDL trước khi gọi các hàm trong tệp này để không giữ kết nối MySQL lúc chờ mạng.
- Không bao giờ ghi khóa API vào log.
"""
import json
import re
import threading
from typing import Any

from openai import OpenAI, OpenAIError

from app.integrations.ai.config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    OPENAI_TIMEOUT_SECONDS,
    ai_ready,
)

_client: OpenAI | None = None
_client_lock = threading.Lock()
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class AiNotConfiguredError(Exception):
    """Chưa cấu hình OPENAI_API_KEY hoặc OPENAI_MODEL trong .env."""


class AiProviderError(Exception):
    """Nhà cung cấp AI lỗi mạng, quá hạn mức hoặc trả về dữ liệu rỗng."""


def get_ai_client() -> OpenAI:
    """Khởi tạo lười (lazy singleton) đối tượng OpenAI dùng chung toàn tiến trình."""
    global _client
    if not ai_ready():
        raise AiNotConfiguredError("Chưa cấu hình khóa hoặc mô hình AI")
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = OpenAI(
                    api_key=OPENAI_API_KEY,
                    base_url=OPENAI_BASE_URL,
                    timeout=OPENAI_TIMEOUT_SECONDS,
                    max_retries=1,
                )
    return _client


def chat_completion(system_prompt: str, messages: list[dict[str, str]]) -> str:
    """Gửi cuộc hội thoại tới AI và trả về nội dung văn bản đã cắt khoảng trắng thừa."""
    client = get_ai_client()
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": system_prompt}, *messages],
        )
        reply = (response.choices[0].message.content or "").strip() if response.choices else ""
    except OpenAIError as error:
        raise AiProviderError("Không gọi được dịch vụ AI") from error
    except Exception as error:
        raise AiProviderError("Lỗi kết nối dịch vụ AI") from error
    if not reply:
        raise AiProviderError("AI trả về nội dung rỗng")
    return reply


def json_completion(system_prompt: str, user_prompt: str) -> Any:
    """Gọi AI sinh kết quả định dạng JSON; trả về None nếu AI chưa bật, lỗi mạng hoặc JSON sai cú pháp."""
    if not ai_ready():
        return None
    try:
        raw = chat_completion(system_prompt, [{"role": "user", "content": user_prompt}])
    except (AiNotConfiguredError, AiProviderError):
        return None
    cleaned = _FENCE_RE.sub("", raw.strip())
    try:
        return json.loads(cleaned)
    except ValueError:
        return None
