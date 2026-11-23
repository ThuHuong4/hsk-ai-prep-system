"""Hỏi Xiang theo lượt làm bài đã lưu (Ôn luyện & Thi thử).

Frontend gửi đoạn chat hiện tại của câu đó; backend tự dựng ngữ cảnh câu hỏi từ CSDL,
giải phóng giao dịch đọc rồi mới gọi AI qua cổng tập trung `app.integrations.ai`.
"""
import threading
import time
from collections import defaultdict, deque

from sqlalchemy.orm import Session

from app.integrations.ai import (
    AiNotConfiguredError,
    AiProviderError,
    XIANG_POST_CHECK_SYSTEM_PROMPT as SYSTEM_PROMPT,
    ai_ready,
    chat_completion,
)
from app.modules.ai_tutor.services.question_context import build_context

MAX_TURNS = 10            # Chỉ gửi 10 tin gần nhất
MAX_CHARS = 500           # Mỗi tin tối đa 500 ký tự
MIN_GAP_SECONDS = 2       # Mỗi học viên cách nhau ít nhất 2 giây
MAX_PER_MINUTE = 20       # Tối đa 20 câu hỏi/phút/học viên

# Giữ tên ngoại lệ rõ nghĩa cho tầng endpoint bắt lỗi
AiNotConfigured = AiNotConfiguredError
AiUnavailable = AiProviderError


class AiBusy(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


_lock = threading.Lock()
_running: set[tuple[int, int, int]] = set()        # (học viên, lượt, câu) đang chờ AI
_recent: dict[int, deque] = defaultdict(deque)      # Thời điểm các lần hỏi gần đây của mỗi học viên


def _acquire(uid: int, key: tuple[int, int, int]) -> None:
    now = time.monotonic()
    with _lock:
        if key in _running:
            raise AiBusy("Xiang đang trả lời câu này, chờ chút nhé")
        times = _recent[uid]
        while times and now - times[0] > 60:
            times.popleft()
        if times and now - times[-1] < MIN_GAP_SECONDS:
            raise AiBusy("Bạn hỏi nhanh quá, đợi 2 giây rồi hỏi tiếp nhé")
        if len(times) >= MAX_PER_MINUTE:
            raise AiBusy("Bạn đã hỏi nhiều trong 1 phút, nghỉ một chút rồi hỏi tiếp nhé")
        times.append(now)
        _running.add(key)


def _release(key: tuple[int, int, int]) -> None:
    with _lock:
        _running.discard(key)


def _clean_history(history: list[dict]) -> list[dict]:
    """Chỉ nhận 2 vai, cắt độ dài; tin cuối phải là của học viên."""
    messages = []
    for m in history[-MAX_TURNS:]:
        role = "user" if m.get("vai") == "hoc_vien" else "assistant"
        content = str(m.get("noi_dung", "")).strip()[:MAX_CHARS]
        if content:
            messages.append({"role": role, "content": content})
    if not messages or messages[-1]["role"] != "user":
        raise AiBusy("Hãy nhập câu hỏi cho Xiang")
    return messages


def ask_xiang(db: Session, uid: int, luot_id: int, cau_hoi_id: int, history: list[dict]) -> str:
    if not ai_ready():
        raise AiNotConfigured()
    context = build_context(db, uid, luot_id, cau_hoi_id)
    db.rollback()  # Giải phóng giao dịch đọc trước khi gọi dịch vụ AI bên ngoài
    messages = _clean_history(history)
    key = (uid, luot_id, cau_hoi_id)
    _acquire(uid, key)
    try:
        return chat_completion(f"{SYSTEM_PROMPT}\n\nNGỮ CẢNH CÂU HỎI:\n{context}", messages)
    finally:
        _release(key)
