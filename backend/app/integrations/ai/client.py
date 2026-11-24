"""Cổng gọi mô hình AI tập trung (Singleton OpenAI-compatible client, tự nạp lại `.env` và bóc JSON bền bỉ).

Quy tắc bắt buộc toàn dự án:
- Luôn đóng/rollback giao dịch CSDL trước khi gọi các hàm trong tệp này để không giữ kết nối MySQL lúc chờ mạng.
- Không bao giờ ghi khóa API vào log.
"""
import json
import re
import threading
import time
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, OpenAIError, RateLimitError

from app.integrations.ai.config import OPENAI_TIMEOUT_SECONDS, ai_ready, current_ai_config

_client: OpenAI | None = None
_client_sig: tuple[str | None, str | None] | None = None
_client_lock = threading.Lock()
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class AiNotConfiguredError(Exception):
    """Chưa cấu hình khóa API hoặc tên mô hình AI trong .env."""


class AiProviderError(Exception):
    """Nhà cung cấp AI lỗi mạng, quá hạn mức hoặc trả về dữ liệu rỗng."""


def get_ai_client() -> OpenAI:
    """Khởi tạo hoặc làm mới đối tượng OpenAI-compatible khi khóa / base_url trong `.env` thay đổi."""
    global _client, _client_sig
    cfg = current_ai_config()
    if not (cfg["api_key"] and cfg["model"]):
        raise AiNotConfiguredError("Chưa cấu hình khóa API hoặc mô hình AI trong backend/.env")
    sig = (cfg["api_key"], cfg["base_url"])
    if _client is None or _client_sig != sig:
        with _client_lock:
            if _client is None or _client_sig != sig:
                _client = OpenAI(
                    api_key=cfg["api_key"],
                    base_url=cfg["base_url"],
                    timeout=OPENAI_TIMEOUT_SECONDS,
                    max_retries=3,
                )
                _client_sig = sig
    return _client


def _friendly_provider_message(error: Exception) -> str:
    if isinstance(error, RateLimitError):
        return "AI miễn phí đang chạm giới hạn số lượt gọi mỗi phút hoặc hết hạn mức ngày. Đợi 15–30 giây rồi bấm thử lại."
    if isinstance(error, APITimeoutError):
        return "AI phản hồi quá thời gian chờ, vui lòng bấm thử lại."
    if isinstance(error, APIConnectionError):
        return "Không kết nối được tới máy chủ AI. Kiểm tra mạng Internet hoặc OPENAI_BASE_URL trong backend/.env."
    if isinstance(error, APIStatusError):
        if error.status_code in (401, 403):
            return "Khóa API AI không hợp lệ hoặc chưa bật quyền truy cập. Kiểm tra lại OPENAI_API_KEY trong backend/.env."
        if error.status_code == 404:
            return "Tên mô hình AI (OPENAI_MODEL) không tồn tại trên cổng đang chọn. Ví dụ với Gemini dùng gemini-2.5-flash."
    return "Dịch vụ AI tạm thời gián đoạn, vui lòng thử lại."


def parse_json_reply(raw: str) -> Any:
    """Bóc dữ liệu JSON từ phản hồi của LLM (chịu được khối ```json ... ``` hoặc lời dẫn ngắn đầu/cuối)."""
    cleaned = _FENCE_RE.sub("", (raw or "").strip()).strip()
    if not cleaned:
        raise ValueError("Empty JSON reply")
    try:
        return json.loads(cleaned)
    except ValueError:
        pass
    # Tìm khối {...} hoặc [...] ngoài cùng nếu model kèm thêm câu giải thích bên ngoài
    pairs = [("{", "}"), ("[", "]")]
    best_start, best_end = None, None
    for open_ch, close_ch in pairs:
        start = cleaned.find(open_ch)
        end = cleaned.rfind(close_ch)
        if start != -1 and end > start and (best_start is None or start < best_start):
            best_start, best_end = start, end
    if best_start is not None and best_end is not None:
        return json.loads(cleaned[best_start:best_end + 1])
    raise ValueError("Invalid JSON reply")


def chat_completion(system_prompt: str, messages: list[dict[str, str]]) -> str:
    """Gửi cuộc hội thoại tới AI (có tự thử lại nhẹ khi chạm giới hạn lượt/phút của gói miễn phí)."""
    cfg = current_ai_config()
    client = get_ai_client()
    model = cfg["model"] or ""
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system_prompt}, *messages],
            )
            reply = (response.choices[0].message.content or "").strip() if response.choices else ""
            if reply:
                return reply
            last_error = AiProviderError("AI trả về nội dung rỗng")
        except RateLimitError as error:
            last_error = error
            if attempt < 2:
                time.sleep(3.5 * (attempt + 1))
                continue
        except OpenAIError as error:
            raise AiProviderError(_friendly_provider_message(error)) from error
        except Exception as error:
            raise AiProviderError("Lỗi kết nối dịch vụ AI") from error
    if isinstance(last_error, AiProviderError):
        raise last_error
    raise AiProviderError(_friendly_provider_message(last_error) if last_error else "Không gọi được dịch vụ AI")


def json_completion(system_prompt: str, user_prompt: str) -> Any:
    """Gọi AI sinh kết quả định dạng JSON; trả về None nếu AI chưa bật, lỗi mạng hoặc JSON sai cú pháp."""
    if not ai_ready():
        return None
    try:
        raw = chat_completion(system_prompt, [{"role": "user", "content": user_prompt}])
    except (AiNotConfiguredError, AiProviderError):
        return None
    try:
        return parse_json_reply(raw)
    except ValueError:
        return None
