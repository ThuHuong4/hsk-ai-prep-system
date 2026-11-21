"""Hỏi Xiang dùng chung cho Khách (giới hạn theo IP) và kết quả kiểm tra vượt của Học viên (giới hạn theo tài khoản).

- Tối đa GUEST_DAILY lượt/ngày/IP, cách nhau tối thiểu 2 giây, mỗi IP chỉ 1 yêu cầu cùng lúc.
- Bộ đếm trong bộ nhớ (khởi động lại máy chủ thì đếm lại); không lưu hội thoại.
- Khóa API lấy từ .env qua openai_config, không ghi khóa hay nội dung vào log.
"""
import importlib
import threading
import time
from datetime import date

from app.core.openai_config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, OPENAI_TIMEOUT_SECONDS, openai_ready

GUEST_DAILY = 10
MIN_GAP_SECONDS = 2
MAX_TURNS = 10
MAX_CHARS = 500

_FALLBACK_PROMPT = (
    "Bạn là Xiang, trợ giảng tiếng Trung thân thiện cho người Việt luyện HSK. "
    "Trả lời ngắn gọn bằng tiếng Việt, giải thích vì sao đáp án đúng, chỉ bàn về câu hỏi trong ngữ cảnh."
)


class GuestLimit(Exception):
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.message = message
        self.retry_after = retry_after


class GuestAiOff(Exception):
    pass


class GuestAiError(Exception):
    pass


_lock = threading.Lock()
_usage: dict[str, list] = {}  # ip -> [ngày, số lượt, lần gọi cuối]
_busy: set[str] = set()
_client = None


def _system_prompt() -> str:
    try:  # dùng chung tính cách Xiang của Học viên nếu có
        return getattr(importlib.import_module("app.modules.ai_tutor.services.xiang_chat"), "SYSTEM_PROMPT", _FALLBACK_PROMPT)
    except Exception:
        return _FALLBACK_PROMPT


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL, timeout=OPENAI_TIMEOUT_SECONDS, max_retries=1)
    return _client


def _acquire(ip: str, daily: int = GUEST_DAILY, out_msg: str = "Bạn đã dùng hết lượt hỏi Xiang hôm nay. Đăng nhập để hỏi thêm.") -> None:
    now, today = time.monotonic(), date.today()
    with _lock:
        if ip in _busy:
            raise GuestLimit("Xiang đang trả lời câu trước, đợi chút nhé.", 2)
        day, count, last = _usage.get(ip, [today, 0, 0.0])
        if day != today:
            day, count = today, 0
        if count >= daily:
            raise GuestLimit(out_msg, 3600)
        if now - last < MIN_GAP_SECONDS:
            raise GuestLimit("Bạn hỏi hơi nhanh, thử lại sau vài giây.", MIN_GAP_SECONDS)
        _usage[ip] = [day, count + 1, now]
        _busy.add(ip)
        if len(_usage) > 5000:  # dọn IP của ngày cũ
            for key in [k for k, v in _usage.items() if v[0] != today]:
                _usage.pop(key, None)


def _release(ip: str) -> None:
    with _lock:
        _busy.discard(ip)


def remaining(ip: str) -> int:
    with _lock:
        day, count, _ = _usage.get(ip, [date.today(), 0, 0.0])
        return GUEST_DAILY - (count if day == date.today() else 0)


def ask(ip: str, context: str, history: list[dict], daily: int = GUEST_DAILY, out_msg: str | None = None) -> str:
    """ip: khóa đếm lượt (IP của Khách, hoặc "hv:<id>" cho Học viên)."""
    if not openai_ready():
        raise GuestAiOff()
    turns = [m for m in history if m.get("noi_dung", "").strip()][-MAX_TURNS:]
    if not turns or turns[-1]["vai"] != "hoc_vien":
        raise ValueError("Tin nhắn cuối phải là câu hỏi của người học")
    messages = [{"role": "user" if m["vai"] == "hoc_vien" else "assistant", "content": m["noi_dung"].strip()[:MAX_CHARS]} for m in turns]
    _acquire(ip, daily, out_msg or "Bạn đã dùng hết lượt hỏi Xiang hôm nay. Đăng nhập để hỏi thêm.")
    try:
        response = _get_client().chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": f"{_system_prompt()}\n\nNGỮ CẢNH CÂU HỎI:\n{context}"}, *messages],
        )
        reply = (response.choices[0].message.content or "").strip() if response.choices else ""
    except Exception as error:  # lỗi mạng/hạn mức của nhà cung cấp AI
        raise GuestAiError() from error
    finally:
        _release(ip)
    if not reply:
        raise GuestAiError()
    return reply
