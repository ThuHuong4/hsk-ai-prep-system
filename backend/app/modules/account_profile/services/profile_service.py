"""Trang Cá nhân của Học viên (mục 3.1, 6.3): hồ sơ, email nhắc, đổi mật khẩu.

- Email chỉ hiển thị, không đổi được. Không trả mat_khau_bam ra ngoài (chỉ trả có/không có mật khẩu).
- Đổi mật khẩu chỉ cho tài khoản có mật khẩu; tài khoản chỉ đăng nhập Google thì không có mục này.
"""
import time
from collections import defaultdict, deque
from threading import Lock

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.common.service_errors import RuleError
from app.modules.practice.services import path_view
from app.security.password_hasher import hash_password, verify_password
from app.security.password_policy import validate_password_strength


class TooManyAttemptsError(Exception):
    pass


# Chặn dò mật khẩu cũ: tối đa 5 lần nhập sai trong 15 phút cho mỗi tài khoản (bộ nhớ tiến trình)
_FAIL_LIMIT, _FAIL_WINDOW = 5, 15 * 60
_fails: dict[int, deque] = defaultdict(deque)
_fails_lock = Lock()


def _recent_fails(uid: int) -> deque:
    q = _fails[uid]
    now = time.monotonic()
    while q and now - q[0] > _FAIL_WINDOW:
        q.popleft()
    return q


def get_profile(db: Session, uid: int) -> dict:
    row = db.execute(
        text("""SELECT n.ho_ten, n.email, n.tao_luc, n.mat_khau_bam IS NOT NULL AS co_mat_khau,
                       n.google_sub IS NOT NULL AS lien_ket_google, n.email_xac_minh_luc IS NOT NULL AS email_da_xac_minh,
                       n.nhan_email_nhac
                FROM nguoi_dung n WHERE n.id = :u"""),
        {"u": uid},
    ).mappings().one()
    stats = path_view.energy_and_kn(db, uid)
    db.rollback()
    return {
        "ho_ten": row["ho_ten"], "email": row["email"], "tham_gia_luc": row["tao_luc"],
        "co_mat_khau": bool(row["co_mat_khau"]), "lien_ket_google": bool(row["lien_ket_google"]),
        "email_da_xac_minh": bool(row["email_da_xac_minh"]),
        "nhan_email_nhac": bool(row["nhan_email_nhac"]),
        "kn": stats["kn"], "chuoi_ngay": stats["chuoi_ngay"]
    }


def update_name(db: Session, uid: int, ho_ten: str) -> None:
    try:
        db.execute(text("UPDATE nguoi_dung SET ho_ten = :t WHERE id = :u"), {"t": ho_ten, "u": uid})
        db.commit()
    except Exception:
        db.rollback()
        raise


def update_reminder(db: Session, uid: int, on: bool) -> None:
    try:
        db.execute(text("UPDATE nguoi_dung SET nhan_email_nhac = :b WHERE id = :u"), {"b": 1 if on else 0, "u": uid})
        db.commit()
    except Exception:
        db.rollback()
        raise


def change_password(db: Session, uid: int, old: str, new: str) -> None:
    with _fails_lock:
        if len(_recent_fails(uid)) >= _FAIL_LIMIT:
            raise TooManyAttemptsError()
    try:
        validate_password_strength(new)
    except ValueError as error:
        raise RuleError(str(error))
    if old == new:
        raise RuleError("Mật khẩu mới phải khác mật khẩu hiện tại")
    new_hash = hash_password(new)  # băm trước khi khóa dòng để giữ khóa ngắn
    try:
        stored = db.execute(text("SELECT mat_khau_bam FROM nguoi_dung WHERE id = :u FOR UPDATE"), {"u": uid}).scalar_one()
        if not stored:
            raise RuleError("Tài khoản đăng nhập bằng Google, không dùng mật khẩu")
        if not verify_password(old, stored):
            db.rollback()
            with _fails_lock:
                _recent_fails(uid).append(time.monotonic())
            raise RuleError("Mật khẩu hiện tại không đúng")
        db.execute(text("UPDATE nguoi_dung SET mat_khau_bam = :h, phien_ban_phien = phien_ban_phien + 1 WHERE id = :u"),
                   {"h": new_hash, "u": uid})
        db.commit()
    except Exception:
        db.rollback()
        raise
    with _fails_lock:
        _fails.pop(uid, None)
