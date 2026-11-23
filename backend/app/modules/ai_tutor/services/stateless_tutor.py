"""Hỏi Xiang không lưu CSDL (dùng cho Khách học thử theo IP, kết quả Kiểm tra vượt và lượt ôn Sổ tay).

- Bộ đếm hạn mức ngày và chống gửi dồn (cooldown 2 giây) giữ trong bộ nhớ.
- Gọi AI thông qua cổng tập trung `app.integrations.ai`.
"""
import threading
import time
from datetime import date

from app.integrations.ai import (
    AiNotConfiguredError,
    AiProviderError,
    XIANG_POST_CHECK_SYSTEM_PROMPT,
    ai_ready,
    chat_completion,
)

GUEST_DAILY = 10
MIN_GAP_SECONDS = 2
MAX_TURNS = 10
MAX_CHARS = 500


class QuotaLimitError(Exception):
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.message = message
        self.retry_after = retry_after


_lock = threading.Lock()
_usage: dict[str, list] = {}  # actor_key -> [ngày, số lượt, lần gọi cuối]
_busy: set[str] = set()


def _acquire(actor_key: str, daily: int, out_msg: str) -> None:
    now, today = time.monotonic(), date.today()
    with _lock:
        if actor_key in _busy:
            raise QuotaLimitError("Xiang đang trả lời câu trước, đợi chút nhé.", 2)
        day, count, last = _usage.get(actor_key, [today, 0, 0.0])
        if day != today:
            day, count = today, 0
        if count >= daily:
            raise QuotaLimitError(out_msg, 3600)
        if now - last < MIN_GAP_SECONDS:
            raise QuotaLimitError("Bạn hỏi hơi nhanh, thử lại sau vài giây.", MIN_GAP_SECONDS)
        _usage[actor_key] = [day, count + 1, now]
        _busy.add(actor_key)
        if len(_usage) > 5000:
            for key in [k for k, v in _usage.items() if v[0] != today]:
                _usage.pop(key, None)


def _release(actor_key: str) -> None:
    with _lock:
        _busy.discard(actor_key)


def remaining_quota(actor_key: str, daily: int = GUEST_DAILY) -> int:
    with _lock:
        day, count, _ = _usage.get(actor_key, [date.today(), 0, 0.0])
        return daily - (count if day == date.today() else 0)


def ask_stateless_xiang(
    actor_key: str,
    context: str,
    history: list[dict],
    daily: int = GUEST_DAILY,
    out_msg: str | None = None,
) -> str:
    """actor_key: IP của Khách hoặc 'hv:<id>' của Học viên."""
    if not ai_ready():
        raise AiNotConfiguredError()
    turns = [m for m in history if m.get("noi_dung", "").strip()][-MAX_TURNS:]
    if not turns or turns[-1]["vai"] != "hoc_vien":
        raise ValueError("Tin nhắn cuối phải là câu hỏi của người học")
    messages = [
        {"role": "user" if m["vai"] == "hoc_vien" else "assistant", "content": m["noi_dung"].strip()[:MAX_CHARS]}
        for m in turns
    ]
    limit_msg = out_msg or "Bạn đã dùng hết lượt hỏi Xiang hôm nay. Đăng nhập để hỏi thêm."
    _acquire(actor_key, daily, limit_msg)
    try:
        return chat_completion(f"{XIANG_POST_CHECK_SYSTEM_PROMPT}\n\nNGỮ CẢNH CÂU HỎI:\n{context}", messages)
    finally:
        _release(actor_key)


# Bí danh tương thích để dễ gọi ngắn gọn
GuestLimit = QuotaLimitError
GuestAiOff = AiNotConfiguredError
GuestAiError = AiProviderError
ask = ask_stateless_xiang
remaining = remaining_quota
