"""Nhật ký yêu cầu xác thực để chặn gửi lặp / thử nhiều lần.

CSDL Xianglingo (19 bảng) không có bảng nhật ký này, nên dữ liệu được giữ trong bộ nhớ
của tiến trình backend. Giới hạn: mất khi khởi động lại server và chỉ đúng khi chạy
một tiến trình (uvicorn mặc định). Chữ ký hàm giữ nguyên để service không phải sửa;
tham số db không còn được dùng.
"""
import threading
import time
from collections import defaultdict, deque

from sqlalchemy.orm import Session

_HOUR = 3600
_lock = threading.Lock()
_by_email: dict[tuple[str, bytes], deque] = defaultdict(deque)
_by_ip: dict[tuple[str, str], deque] = defaultdict(deque)


def _prune(q: deque, now: float, window: float = _HOUR) -> None:
    while q and q[0] <= now - window:
        q.popleft()


def record_auth_request(db: Session, muc_dich: str, bam_email: bytes, dia_chi_ip: str) -> None:
    now = time.monotonic()
    with _lock:
        _by_email[(muc_dich, bam_email)].append(now)
        _by_ip[(muc_dich, dia_chi_ip)].append(now)


def get_email_request_stats(db: Session, muc_dich: str, bam_email: bytes) -> dict:
    now = time.monotonic()
    with _lock:
        q = _by_email.get((muc_dich, bam_email))
        if not q:
            return {"so_lan_1_gio": 0, "giay_tu_lan_cuoi": None}
        _prune(q, now)
        if not q:
            return {"so_lan_1_gio": 0, "giay_tu_lan_cuoi": None}
        return {"so_lan_1_gio": len(q), "giay_tu_lan_cuoi": int(now - q[-1])}


def count_ip_requests_last_hour(db: Session, muc_dich: str, dia_chi_ip: str) -> int:
    now = time.monotonic()
    with _lock:
        q = _by_ip.get((muc_dich, dia_chi_ip))
        if not q:
            return 0
        _prune(q, now)
        return len(q)


def delete_old_auth_requests(db: Session, retention_days: int, batch_size: int = 1000) -> int:
    # Bộ nhớ chỉ cần giữ 1 giờ gần nhất; xóa các khóa đã rỗng
    now = time.monotonic()
    removed = 0
    with _lock:
        for store in (_by_email, _by_ip):
            for key in list(store.keys()):
                _prune(store[key], now)
                if not store[key]:
                    del store[key]
                    removed += 1
    return removed
